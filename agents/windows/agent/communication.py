"""REST and WebSocket communication with the Heimdall backend.

Uses httpx for async REST calls and the websockets library for persistent
WebSocket connections.  Every outbound REST request carries the device token
in the ``X-Device-Token`` header for authentication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import httpx
import websockets
from websockets.asyncio.client import ClientConnection

from .config import AgentConfig

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# REST client
# ---------------------------------------------------------------------------

class RestClient:
    """Async HTTP client for the Heimdall agent REST endpoints.

    All requests are authenticated via the ``X-Device-Token`` header whose
    value is read from *config.device_token*.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle -----------------------------------------------------------

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._config.api_base,
                headers={"X-Device-Token": self._config.device_token},
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        """Shut down the underlying HTTP client gracefully."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # -- endpoints -----------------------------------------------------------

    async def send_heartbeat(self, active_app: str | None = None) -> dict[str, Any]:
        """POST /agent/heartbeat

        Parameters
        ----------
        active_app:
            The currently focused application name, or *None* if the screen
            is idle / locked.

        Returns
        -------
        dict
            The JSON response body from the server.
        """
        client = await self._ensure_client()
        payload: dict[str, Any] = {
            "timestamp": _utcnow_iso(),
            "active_app": active_app,
        }
        log.debug("Sending heartbeat: %s", payload)
        try:
            resp = await client.post("/agent/heartbeat", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            log.debug("Heartbeat response: %s", data)
            return data
        except httpx.HTTPStatusError as exc:
            log.error(
                "Heartbeat failed with HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.HTTPError as exc:
            log.error("Heartbeat request error: %s", exc)
            raise

    async def send_usage_event(
        self,
        *,
        app_package: str | None = None,
        app_group_id: str | None = None,
        event_type: str,
        started_at: str | None = None,
        ended_at: str | None = None,
        duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        """POST /agent/usage-event

        Parameters
        ----------
        app_package:
            OS-level application identifier (e.g. executable name).
        app_group_id:
            Heimdall app-group UUID this application belongs to.
        event_type:
            One of ``"start"``, ``"stop"``, or ``"blocked"``.
        started_at:
            ISO-8601 timestamp when the usage session started.
        ended_at:
            ISO-8601 timestamp when the usage session ended.
        duration_seconds:
            Duration of the session in whole seconds.

        Returns
        -------
        dict
            The JSON response body from the server.
        """
        client = await self._ensure_client()
        payload: dict[str, Any] = {
            "app_package": app_package,
            "app_group_id": app_group_id,
            "event_type": event_type,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_seconds,
        }
        log.debug("Sending usage event: %s", payload)
        try:
            resp = await client.post("/agent/usage-event", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            log.debug("Usage event response: %s", data)
            return data
        except httpx.HTTPStatusError as exc:
            log.error(
                "Usage event failed with HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.HTTPError as exc:
            log.error("Usage event request error: %s", exc)
            raise

    async def fetch_rules(self) -> dict[str, Any]:
        """GET /agent/rules/current

        Returns
        -------
        dict
            Parsed JSON with keys ``day_type``, ``time_windows``,
            ``group_limits``, ``daily_limit_minutes``, and ``active_tans``.
        """
        client = await self._ensure_client()
        log.debug("Fetching current rules")
        try:
            resp = await client.get("/agent/rules/current")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            log.debug("Rules response: %s", data)
            return data
        except httpx.HTTPStatusError as exc:
            log.error(
                "Fetch rules failed with HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.HTTPError as exc:
            log.error("Fetch rules request error: %s", exc)
            raise


# ---------------------------------------------------------------------------
# WebSocket client
# ---------------------------------------------------------------------------

# Type alias for the message callback.  The callback receives the parsed JSON
# dict and may be a coroutine function or a plain callable.
OnMessageCallback = Callable[[dict[str, Any]], Any] | Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]

# Reconnection parameters (exponential back-off)
_WS_INITIAL_BACKOFF: float = 1.0  # seconds
_WS_MAX_BACKOFF: float = 60.0  # seconds
_WS_BACKOFF_FACTOR: float = 2.0


class WsClient:
    """Persistent WebSocket connection to the Heimdall backend.

    The connection lifecycle:

    1.  ``connect()`` opens the socket and performs the token handshake.
    2.  ``run()`` enters the main loop that reads incoming messages and
        dispatches them to *on_message*.  It also drains an internal
        ``asyncio.Queue`` to send outgoing messages (e.g. heartbeats).
    3.  ``disconnect()`` cleanly shuts the socket down.

    If the connection drops, ``run()`` will automatically reconnect with
    exponential back-off.
    """

    def __init__(
        self,
        config: AgentConfig,
        on_message: OnMessageCallback,
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._ws: ClientConnection | None = None
        self._outgoing: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._running: bool = False
        self._heartbeat_task: asyncio.Task[None] | None = None

    # -- public API ----------------------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket and authenticate with the device token.

        Raises
        ------
        websockets.exceptions.WebSocketException
            If the connection or authentication handshake fails.
        """
        url = self._config.ws_url
        log.info("Connecting to WebSocket at %s", url)
        self._ws = await websockets.connect(url)

        # Step 1: send device token as plain text.
        await self._ws.send(self._config.device_token)
        log.debug("Sent device token for authentication")

        # Step 2: wait for auth_ok.
        raw = await self._ws.recv()
        msg = json.loads(raw)
        if msg.get("type") != "auth_ok":
            log.error("WebSocket authentication failed: %s", msg)
            await self._ws.close()
            self._ws = None
            raise RuntimeError(f"WebSocket auth failed: {msg}")

        device_id = msg.get("device_id")
        log.info("WebSocket authenticated (device_id=%s)", device_id)

    async def enqueue(self, message: dict[str, Any]) -> None:
        """Place a message on the outgoing queue to be sent over the socket."""
        await self._outgoing.put(message)

    async def run(self) -> None:
        """Main loop with automatic reconnection.

        This coroutine runs indefinitely until ``disconnect()`` is called
        (which sets ``_running = False``).
        """
        self._running = True
        backoff = _WS_INITIAL_BACKOFF

        while self._running:
            try:
                # Ensure we have a live connection.
                if self._ws is None or self._ws.close_code is not None:
                    await self.connect()

                # Reset back-off on successful connection.
                backoff = _WS_INITIAL_BACKOFF

                # Start the periodic heartbeat producer.
                self._heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(),
                    name="ws-heartbeat",
                )

                # Run reader and writer concurrently; if either finishes
                # (e.g. socket closed), cancel the other.
                reader = asyncio.create_task(self._read_loop(), name="ws-reader")
                writer = asyncio.create_task(self._write_loop(), name="ws-writer")

                done, pending = await asyncio.wait(
                    {reader, writer, self._heartbeat_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Cancel remaining tasks.
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Propagate exceptions from finished tasks so they are logged.
                for task in done:
                    if task.exception() is not None:
                        raise task.exception()  # type: ignore[misc]

            except asyncio.CancelledError:
                log.debug("WsClient.run() cancelled")
                break
            except Exception:
                if not self._running:
                    break
                log.warning(
                    "WebSocket connection lost, reconnecting in %.1fs ...",
                    backoff,
                    exc_info=True,
                )
                await self._cleanup_ws()
                await asyncio.sleep(backoff)
                backoff = min(backoff * _WS_BACKOFF_FACTOR, _WS_MAX_BACKOFF)

        await self._cleanup_ws()
        log.info("WsClient.run() exited")

    async def disconnect(self) -> None:
        """Signal the run-loop to stop and close the socket."""
        log.info("Disconnecting WebSocket")
        self._running = False
        await self._cleanup_ws()

    # -- internals -----------------------------------------------------------

    async def _cleanup_ws(self) -> None:
        """Close the WebSocket connection if it is still open."""
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                log.debug("Ignoring error while closing WebSocket", exc_info=True)
            self._ws = None

    async def _read_loop(self) -> None:
        """Continuously read messages from the WebSocket and dispatch them."""
        assert self._ws is not None
        async for raw in self._ws:
            try:
                msg: dict[str, Any] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                log.warning("Received non-JSON WebSocket message: %r", raw)
                continue

            msg_type = msg.get("type", "<unknown>")
            log.debug("WS received message type=%s", msg_type)

            try:
                result = self._on_message(msg)
                # Support both sync and async callbacks.
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                log.exception("Error in on_message callback for type=%s", msg_type)

    async def _write_loop(self) -> None:
        """Drain the outgoing queue and send messages over the socket."""
        assert self._ws is not None
        while True:
            msg = await self._outgoing.get()
            try:
                payload = json.dumps(msg)
                await self._ws.send(payload)
                log.debug("WS sent: %s", payload)
            except Exception:
                log.exception("Failed to send WS message: %s", msg)
                raise  # break out so run() can reconnect

    async def _heartbeat_loop(self) -> None:
        """Periodically enqueue a heartbeat message."""
        interval = self._config.heartbeat_interval
        while True:
            await asyncio.sleep(interval)
            await self.enqueue({"type": "heartbeat"})
            log.debug("Enqueued WS heartbeat")
