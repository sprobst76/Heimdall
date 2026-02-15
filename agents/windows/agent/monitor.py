"""Process monitoring for the Heimdall Windows agent.

Detects the active foreground window and tracks application usage duration.
Uses psutil for process information and pywin32 for foreground window
detection on Windows.  On non-Windows platforms the win32 imports are
gracefully skipped so the module can still be loaded for development and
testing (a dummy foreground result is returned instead).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import psutil

from .config import AgentConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional win32 imports -- only available on Windows.
# ---------------------------------------------------------------------------
try:
    import win32gui  # type: ignore[import-untyped]
    import win32process  # type: ignore[import-untyped]

    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    logger.debug(
        "pywin32 not available; foreground detection will use dummy values"
    )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class AppSession:
    """Represents an active app usage session."""

    executable: str  # e.g. "minecraft.exe"
    window_title: str
    app_group_id: str | None  # mapped from config
    pid: int
    started_at: datetime  # when this app became foreground


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------
class ProcessMonitor:
    """Polls the foreground window at a fixed interval and fires a callback
    whenever the active application changes."""

    def __init__(
        self,
        config: AgentConfig,
        on_app_change: Callable[
            [AppSession | None, AppSession | None], object
        ],
    ) -> None:
        """
        Parameters
        ----------
        config:
            AgentConfig instance that supplies ``monitor_interval`` and
            ``app_group_map``.
        on_app_change:
            Async callback invoked as
            ``await on_app_change(old_session, new_session)`` when the
            foreground application changes.  *old_session* carries the ended
            session (with its ``started_at`` timestamp so callers can compute
            the duration) and *new_session* carries the newly started session.
            Either argument may be ``None`` at the edges (e.g. first
            detection or when the desktop / lock screen is in front).
        """
        self._config = config
        self._on_app_change = on_app_change
        self._current_session: AppSession | None = None
        self._simulated_app: tuple[str, str, int] | None = None

    # -- Public helpers -----------------------------------------------------

    @property
    def current_session(self) -> AppSession | None:
        """The currently tracked foreground app session."""
        return self._current_session

    # -- Simulation (for remote control / testing) ---------------------------

    def simulate_foreground(
        self, executable: str, window_title: str = "Simulated Window",
    ) -> None:
        """Inject a fake foreground app for remote testing."""
        self._simulated_app = (executable, window_title, 99999)
        logger.info("Simulated foreground: %s", executable)

    def clear_simulation(self) -> None:
        """Clear the simulated foreground app."""
        self._simulated_app = None
        logger.info("Cleared foreground simulation")

    # -- Foreground detection -----------------------------------------------

    def get_foreground_app(self) -> tuple[str, str, int] | None:
        """Return ``(executable_name, window_title, pid)`` of the foreground
        window, or ``None`` if detection fails.

        If a simulated app has been set via :meth:`simulate_foreground`, that
        value is returned instead of the real foreground window.

        On non-Windows platforms a dummy value is returned so the rest of the
        module can be exercised during development.
        """
        if self._simulated_app is not None:
            return self._simulated_app

        return self._detect_foreground_real()

    @staticmethod
    def _detect_foreground_real() -> tuple[str, str, int] | None:
        """Detect the real foreground window (platform-dependent)."""
        if not _HAS_WIN32:
            # Return a deterministic dummy for testing / dev on macOS / Linux.
            return ("dummy.exe", "Dummy Window", 0)

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            window_title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            if pid <= 0:
                return None

            try:
                proc = psutil.Process(pid)
                executable = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None

            return (executable, window_title, pid)
        except Exception:  # noqa: BLE001
            logger.debug("Failed to detect foreground window", exc_info=True)
            return None

    # -- Executable -> app group mapping ------------------------------------

    def _map_to_group(self, executable: str) -> str | None:
        """Map an executable name to an ``app_group_id`` using
        ``config.app_group_map``.

        The lookup is case-insensitive.  Returns ``None`` when the
        executable is not present in the map.
        """
        return self._config.app_group_map.get(executable.lower())

    # -- Polling ------------------------------------------------------------

    async def poll(self) -> None:
        """Single poll iteration.

        Checks the current foreground application, compares it to the
        previously tracked session, and fires the *on_app_change* callback
        when a transition is detected.
        """
        fg = self.get_foreground_app()  # uses simulation if active

        if fg is None:
            # Could not determine the foreground app -- if we had a session,
            # treat this as the user leaving the tracked app.
            if self._current_session is not None:
                old = self._current_session
                self._current_session = None
                logger.info(
                    "Foreground app lost (was %s)", old.executable
                )
                await self._on_app_change(old, None)
            return

        executable, window_title, pid = fg

        # Check whether the foreground app is still the same process.
        if (
            self._current_session is not None
            and self._current_session.executable == executable
            and self._current_session.pid == pid
        ):
            # Same app, same process -- nothing to do.
            return

        # A change has occurred.
        old_session = self._current_session
        app_group_id = self._map_to_group(executable)

        new_session = AppSession(
            executable=executable,
            window_title=window_title,
            app_group_id=app_group_id,
            pid=pid,
            started_at=datetime.now(timezone.utc),
        )

        self._current_session = new_session

        old_name = old_session.executable if old_session else None
        logger.info(
            "Foreground change: %s -> %s (group=%s)",
            old_name,
            executable,
            app_group_id,
        )

        await self._on_app_change(old_session, new_session)

    # -- Main loop ----------------------------------------------------------

    async def run(self, stop_event: asyncio.Event) -> None:
        """Main monitoring loop.

        Polls every ``config.monitor_interval`` seconds until *stop_event*
        is set.
        """
        interval = self._config.monitor_interval
        logger.info(
            "Process monitor started (interval=%ds)", interval
        )

        while not stop_event.is_set():
            try:
                await self.poll()
            except Exception:  # noqa: BLE001
                logger.exception("Error during monitor poll")

            # Wait for the interval, but break early if the stop event fires.
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=interval
                )
                # If wait_for returns without timeout, the event was set.
                break
            except asyncio.TimeoutError:
                # Normal case -- interval elapsed, loop again.
                pass

        # If we still have an active session when shutting down, report it.
        if self._current_session is not None:
            old = self._current_session
            self._current_session = None
            logger.info(
                "Monitor stopping; closing session for %s", old.executable
            )
            try:
                await self._on_app_change(old, None)
            except Exception:  # noqa: BLE001
                logger.exception("Error firing final app-change callback")

        logger.info("Process monitor stopped")
