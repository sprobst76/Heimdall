"""Tests for agent.offline_cache."""

from __future__ import annotations

from agent.offline_cache import OfflineCache


def test_queue_usage_event(offline_cache: OfflineCache) -> None:
    """A queued usage event appears in the pending list."""
    offline_cache.queue_usage_event({"app": "chrome.exe", "event_type": "start"})

    events = offline_cache.get_pending_events()
    assert len(events) == 1
    row_id, event_type, payload = events[0]
    assert event_type == "usage_event"
    assert payload["app"] == "chrome.exe"


def test_queue_heartbeat(offline_cache: OfflineCache) -> None:
    """A queued heartbeat appears in the pending list."""
    offline_cache.queue_heartbeat({"timestamp": "2025-01-01T00:00:00Z"})

    events = offline_cache.get_pending_events()
    assert len(events) == 1
    _, event_type, payload = events[0]
    assert event_type == "heartbeat"
    assert "timestamp" in payload


def test_mark_synced(offline_cache: OfflineCache) -> None:
    """Marking an event as synced removes it from the pending list."""
    offline_cache.queue_usage_event({"x": 1})
    events = offline_cache.get_pending_events()
    assert len(events) == 1

    offline_cache.mark_synced(events[0][0])

    assert offline_cache.get_pending_events() == []


def test_mark_synced_batch(offline_cache: OfflineCache) -> None:
    """Batch-marking events as synced works correctly."""
    for i in range(5):
        offline_cache.queue_usage_event({"i": i})

    events = offline_cache.get_pending_events()
    assert len(events) == 5

    ids = [e[0] for e in events[:3]]
    offline_cache.mark_synced_batch(ids)

    remaining = offline_cache.get_pending_events()
    assert len(remaining) == 2


def test_cache_rules(offline_cache: OfflineCache) -> None:
    """Rules can be cached and retrieved."""
    rules = {"daily_limit_minutes": 120, "groups": []}

    assert offline_cache.get_cached_rules() is None

    offline_cache.cache_rules(rules)
    cached = offline_cache.get_cached_rules()
    assert cached is not None
    assert cached["daily_limit_minutes"] == 120


def test_cache_rules_upsert(offline_cache: OfflineCache) -> None:
    """Caching rules a second time overwrites the first."""
    offline_cache.cache_rules({"version": 1})
    offline_cache.cache_rules({"version": 2})

    cached = offline_cache.get_cached_rules()
    assert cached is not None
    assert cached["version"] == 2


def test_pending_count(offline_cache: OfflineCache) -> None:
    """pending_count returns the number of unsynced events."""
    assert offline_cache.pending_count() == 0

    offline_cache.queue_usage_event({"a": 1})
    offline_cache.queue_heartbeat({"b": 2})
    assert offline_cache.pending_count() == 2

    events = offline_cache.get_pending_events()
    offline_cache.mark_synced(events[0][0])
    assert offline_cache.pending_count() == 1


def test_cleanup(offline_cache: OfflineCache) -> None:
    """Cleanup removes old synced events but keeps unsynced ones."""
    offline_cache.queue_usage_event({"old": True})
    events = offline_cache.get_pending_events()
    offline_cache.mark_synced(events[0][0])

    # Manually backdate the event so cleanup considers it old
    offline_cache._conn.execute(
        "UPDATE pending_events SET created_at = '2020-01-01T00:00:00+00:00'"
    )
    offline_cache._conn.commit()

    offline_cache.queue_usage_event({"new": True})

    offline_cache.cleanup(days=1)

    # The old synced event was cleaned up, the new unsynced one remains
    remaining = offline_cache.get_pending_events()
    assert len(remaining) == 1
    assert remaining[0][2]["new"] is True


def test_get_pending_events_limit(offline_cache: OfflineCache) -> None:
    """get_pending_events respects the limit parameter."""
    for i in range(10):
        offline_cache.queue_usage_event({"i": i})

    events = offline_cache.get_pending_events(limit=3)
    assert len(events) == 3
