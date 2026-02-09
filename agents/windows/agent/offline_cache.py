"""SQLite offline cache for the Heimdall Windows agent.

When the backend is unreachable, usage events and heartbeats are queued
locally in a SQLite database and synced once the connection is restored.
The database file is stored in the same configuration directory as
``agent_config.json``.

This module is **synchronous** (plain ``sqlite3``) and is expected to be
called from a worker thread so that the async event-loop is never blocked.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import _config_dir

log = logging.getLogger(__name__)

_DB_FILENAME = "offline_cache.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS pending_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    payload    TEXT    NOT NULL,
    event_type TEXT    NOT NULL CHECK (event_type IN ('usage_event', 'heartbeat')),
    created_at TEXT    NOT NULL,
    synced     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cached_rules (
    id         INTEGER PRIMARY KEY,
    rules_json TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
"""


class OfflineCache:
    """Persistent local queue backed by SQLite.

    Parameters
    ----------
    db_path:
        Explicit path to the database file.  When *None* (the default) the
        file is placed inside :func:`.config._config_dir`.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path: Path = db_path or (_config_dir() / _DB_FILENAME)
        log.info("Opening offline cache at %s", self._db_path)
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._create_tables()

    # -- bootstrap ------------------------------------------------------------

    def _create_tables(self) -> None:
        """Create the schema tables if they do not already exist."""
        with self._conn:
            self._conn.executescript(_SCHEMA)
        log.debug("Offline cache tables ensured.")

    # -- event queuing --------------------------------------------------------

    def queue_usage_event(self, payload: dict) -> None:
        """Insert a usage event into the pending queue."""
        self._insert_event(payload, "usage_event")

    def queue_heartbeat(self, payload: dict) -> None:
        """Insert a heartbeat into the pending queue."""
        self._insert_event(payload, "heartbeat")

    def _insert_event(self, payload: dict, event_type: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, default=str)
        with self._conn:
            self._conn.execute(
                "INSERT INTO pending_events (payload, event_type, created_at) "
                "VALUES (?, ?, ?)",
                (payload_json, event_type, now),
            )
        log.debug("Queued %s event (%d bytes)", event_type, len(payload_json))

    # -- retrieval / syncing --------------------------------------------------

    def get_pending_events(self, limit: int = 50) -> list[tuple[int, str, dict]]:
        """Return up to *limit* unsynced events.

        Each element is a tuple of ``(id, event_type, payload)`` where
        *payload* has already been deserialised from JSON.
        """
        cursor = self._conn.execute(
            "SELECT id, event_type, payload FROM pending_events "
            "WHERE synced = 0 ORDER BY id ASC LIMIT ?",
            (limit,),
        )
        rows: list[tuple[int, str, dict]] = []
        for row_id, event_type, payload_json in cursor.fetchall():
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                log.warning("Corrupt payload for event %d, skipping", row_id)
                continue
            rows.append((row_id, event_type, payload))
        return rows

    def mark_synced(self, event_id: int) -> None:
        """Mark a single event as synced."""
        with self._conn:
            self._conn.execute(
                "UPDATE pending_events SET synced = 1 WHERE id = ?",
                (event_id,),
            )

    def mark_synced_batch(self, event_ids: list[int]) -> None:
        """Mark multiple events as synced in a single transaction."""
        if not event_ids:
            return
        placeholders = ",".join("?" for _ in event_ids)
        with self._conn:
            self._conn.execute(
                f"UPDATE pending_events SET synced = 1 WHERE id IN ({placeholders})",
                event_ids,
            )
        log.debug("Marked %d events as synced.", len(event_ids))

    # -- rule caching ---------------------------------------------------------

    def cache_rules(self, rules: dict) -> None:
        """Upsert the latest rules snapshot into the local cache.

        A single row with ``id = 1`` is maintained so that this is always an
        upsert rather than an ever-growing table.
        """
        now = datetime.now(timezone.utc).isoformat()
        rules_json = json.dumps(rules, default=str)
        with self._conn:
            self._conn.execute(
                "INSERT INTO cached_rules (id, rules_json, updated_at) "
                "VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET rules_json = excluded.rules_json, "
                "updated_at = excluded.updated_at",
                (rules_json, now),
            )
        log.debug("Cached rules snapshot (%d bytes).", len(rules_json))

    def get_cached_rules(self) -> dict | None:
        """Return the last cached rules, or *None* if no cache exists."""
        cursor = self._conn.execute(
            "SELECT rules_json FROM cached_rules WHERE id = 1",
        )
        row = cursor.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            log.warning("Corrupt cached rules JSON, returning None.")
            return None

    # -- housekeeping ---------------------------------------------------------

    def pending_count(self) -> int:
        """Return the number of unsynced events still in the queue."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM pending_events WHERE synced = 0",
        )
        return cursor.fetchone()[0]

    def cleanup(self, days: int = 7) -> None:
        """Delete synced events older than *days* days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._conn:
            result = self._conn.execute(
                "DELETE FROM pending_events WHERE synced = 1 AND created_at < ?",
                (cutoff,),
            )
        log.info("Cleaned up %d old synced events (older than %d days).", result.rowcount, days)
