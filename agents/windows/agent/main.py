"""Heimdall Windows Agent — main entry point.

Orchestrates every subsystem:

* **ProcessMonitor** – detects foreground-window changes
* **AppBlocker** – terminates processes in blocked app-groups
* **BlockingOverlay** – displays a blocking screen to the child
* **RestClient / WsClient** – communicates with the Heimdall backend
* **OfflineCache** – queues events when the backend is unreachable
* **TrayIcon** – system-tray presence for status & TAN entry

Supports multiple run modes:

1. **Console** (default) – ``python -m agent.main``
2. **Demo** – ``python -m agent.main --demo`` (no backend required)
3. **Demo + Remote** – ``python -m agent.main --demo --remote-control``
4. **Windows Service** – ``python -m agent.main --service``
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from .blocker import AppBlocker
from .communication import RestClient, WsClient
from .config import AgentConfig
from .monitor import AppSession, ProcessMonitor
from .offline_cache import OfflineCache
from .overlay import BlockingOverlay
from .tray_ui import TrayIcon

log = logging.getLogger("heimdall")

# ---------------------------------------------------------------------------
# The agent orchestrator
# ---------------------------------------------------------------------------


class HeimdallAgent:
    """Central coordinator that wires all subsystems together."""

    def __init__(
        self,
        config: AgentConfig,
        *,
        demo_mode: bool = False,
        remote_control: bool = False,
        remote_port: int = 9876,
    ) -> None:
        self._config = config
        self._demo_mode = demo_mode

        # Core subsystems (always needed)
        self._blocker = AppBlocker(config)
        self._overlay = BlockingOverlay(config)
        self._tray = TrayIcon(config)
        self._monitor = ProcessMonitor(config, on_app_change=self._on_app_change)

        # Backend subsystems (skipped in demo mode)
        if not demo_mode:
            self._rest = RestClient(config)
            self._cache = OfflineCache()
            self._ws = WsClient(config, on_message=self._on_ws_message)

        # Remote control server (optional)
        self._remote = None
        if remote_control:
            from .remote_control import RemoteControlServer
            self._remote = RemoteControlServer(port=remote_port, agent=self)

        # State
        self._rules: dict[str, Any] = {}
        self._stop_event = asyncio.Event()
        self._online = False
        self._totp_config: dict[str, Any] | None = None
        self._totp_override_until: datetime | None = None  # local TOTP override expiry

        # Wire callbacks
        self._blocker.on_block_action = self._on_block_action
        self._overlay.on_tan_entered = self._on_tan_entered
        self._overlay.on_totp_entered = self._on_totp_entered
        self._tray.on_tan_entry = lambda: self._overlay._show_tan_dialog()
        self._tray.on_quit = self._request_stop

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start all subsystems and run until stopped."""
        mode = "DEMO MODE" if self._demo_mode else "normal mode"
        log.info("Heimdall Agent v0.1.0 starting (%s) …", mode)

        if not self._demo_mode and not self._config.is_registered:
            log.error(
                "Agent is not registered (no device_token). "
                "Run registration first or set HEIMDALL_DEVICE_TOKEN."
            )
            return

        # Initial rules
        if self._demo_mode:
            from .demo import get_demo_rules
            self._apply_rules(get_demo_rules())
            log.info("Demo rules applied.")
        else:
            await self._fetch_and_cache_rules()

        # Start tray icon in a dedicated thread (it blocks)
        tray_thread = threading.Thread(
            target=self._tray.run, daemon=True, name="heimdall-tray"
        )
        tray_thread.start()

        # Launch concurrent tasks — only core tasks in demo mode
        tasks = [
            asyncio.create_task(self._monitor.run(self._stop_event), name="monitor"),
            asyncio.create_task(self._enforce_loop(), name="enforce"),
        ]

        if not self._demo_mode:
            tasks.extend([
                asyncio.create_task(self._ws.run(), name="websocket"),
                asyncio.create_task(self._heartbeat_loop(), name="heartbeat"),
                asyncio.create_task(self._rule_poll_loop(), name="rule-poll"),
                asyncio.create_task(self._sync_loop(), name="sync"),
            ])

        if self._remote is not None:
            tasks.append(
                asyncio.create_task(self._remote.run(), name="remote-control"),
            )

        log.info("All subsystems started.")
        self._tray.update_status("connected")
        self._online = True

        # Wait for stop signal
        await self._stop_event.wait()

        log.info("Shutdown requested — cancelling tasks …")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        if not self._demo_mode:
            await self._rest.close()
            await self._ws.disconnect()
        self._tray.stop()
        log.info("Heimdall Agent stopped.")

    def _request_stop(self) -> None:
        """Thread-safe stop request."""
        log.info("Stop requested.")
        self._stop_event.set()

    # ------------------------------------------------------------------
    # App change callback (from ProcessMonitor)
    # ------------------------------------------------------------------

    async def _on_app_change(
        self,
        old_session: AppSession | None,
        new_session: AppSession | None,
    ) -> None:
        """Called by the monitor when the foreground app changes."""
        if self._demo_mode:
            # In demo mode, just log — no backend to report to
            old_name = old_session.executable if old_session else None
            new_name = new_session.executable if new_session else None
            log.debug("Demo app change: %s -> %s", old_name, new_name)
            return

        now = datetime.now(timezone.utc)

        # Report the ended session
        if old_session is not None:
            duration = int((now - old_session.started_at).total_seconds())
            await self._send_usage_event(
                app_package=old_session.executable,
                app_group_id=old_session.app_group_id,
                event_type="stop",
                started_at=old_session.started_at.isoformat(),
                ended_at=now.isoformat(),
                duration_seconds=duration,
            )

        # Report the new session
        if new_session is not None:
            await self._send_usage_event(
                app_package=new_session.executable,
                app_group_id=new_session.app_group_id,
                event_type="start",
                started_at=new_session.started_at.isoformat(),
            )

    # ------------------------------------------------------------------
    # Usage event (with offline fallback)
    # ------------------------------------------------------------------

    async def _send_usage_event(self, **kwargs: Any) -> None:
        """Send a usage event to the backend, falling back to the cache."""
        try:
            await self._rest.send_usage_event(**kwargs)
        except Exception:
            log.debug("Backend unreachable — caching usage event locally.")
            self._cache.queue_usage_event(kwargs)
            self._set_offline()

    # ------------------------------------------------------------------
    # Heartbeat loop (REST-based, separate from WS heartbeat)
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Send periodic REST heartbeats."""
        interval = self._config.heartbeat_interval
        while not self._stop_event.is_set():
            active = self._monitor.current_session
            active_app = active.executable if active else None
            try:
                await self._rest.send_heartbeat(active_app=active_app)
                if not self._online:
                    self._set_online()
            except Exception:
                log.debug("Heartbeat failed — caching.")
                self._cache.queue_heartbeat({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "active_app": active_app,
                })
                self._set_offline()

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Rule polling (REST fallback when WS is down)
    # ------------------------------------------------------------------

    async def _rule_poll_loop(self) -> None:
        """Periodically fetch rules via REST as a WS fallback."""
        interval = self._config.rule_poll_interval
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
            await self._fetch_and_cache_rules()

    async def _fetch_and_cache_rules(self) -> None:
        """Fetch rules via REST and apply them."""
        try:
            rules = await self._rest.fetch_rules()
            self._apply_rules(rules)
            self._cache.cache_rules(rules)
            if not self._online:
                self._set_online()
        except Exception:
            log.debug("Rule fetch failed — using cached rules.")
            cached = self._cache.get_cached_rules()
            if cached:
                self._apply_rules(cached)
            self._set_offline()

    def _apply_rules(self, rules: dict[str, Any]) -> None:
        """Apply a resolved-rules dict: update blocked groups and tray."""
        self._rules = rules
        # Cache TOTP config for offline validation
        self._totp_config = rules.get("totp_config")
        daily_limit = rules.get("daily_limit_minutes")
        group_limits = rules.get("group_limits", [])

        # Update tray with group time info
        group_times: dict[str, tuple[int, int]] = {}
        for gl in group_limits:
            name = gl.get("group_name", gl.get("app_group_id", "?"))
            limit = gl.get("limit_minutes", 0)
            used = gl.get("used_minutes", 0)
            group_times[name] = (used, limit)

            # Block groups that have exceeded their limit
            gid = gl.get("app_group_id")
            if gid and used >= limit > 0:
                self._blocker.block_group(gid)
            elif gid:
                self._blocker.unblock_group(gid)

        self._tray.update_group_times(group_times)

        # Check for warning state (any group < 5 min remaining)
        has_warning = any(
            0 < (lim - used) <= 5
            for used, lim in group_times.values()
            if lim > 0
        )
        if self._blocker.blocked_groups:
            self._tray.update_status("blocked")
        elif has_warning:
            self._tray.update_status("warning")
        elif self._online:
            self._tray.update_status("connected")

    # ------------------------------------------------------------------
    # Enforcement loop
    # ------------------------------------------------------------------

    async def _enforce_loop(self) -> None:
        """Periodically enforce blocking on the current session."""
        while not self._stop_event.is_set():
            # Skip enforcement while a TOTP override is active
            now = datetime.now(timezone.utc)
            if self._totp_override_until is None or now >= self._totp_override_until:
                self._totp_override_until = None  # expired — clear it
                await self._blocker.enforce(self._monitor.current_session)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._config.monitor_interval)
                break
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Sync loop (drain offline cache)
    # ------------------------------------------------------------------

    async def _sync_loop(self) -> None:
        """Periodically sync cached offline events to the backend."""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30)
                break
            except asyncio.TimeoutError:
                pass

            pending = self._cache.get_pending_events(limit=50)
            if not pending:
                continue

            synced_ids: list[int] = []
            for event_id, event_type, payload in pending:
                try:
                    if event_type == "usage_event":
                        await self._rest.send_usage_event(**payload)
                    elif event_type == "heartbeat":
                        await self._rest.send_heartbeat(
                            active_app=payload.get("active_app"),
                        )
                    synced_ids.append(event_id)
                except Exception:
                    # Backend still unreachable — stop trying this batch
                    break

            if synced_ids:
                self._cache.mark_synced_batch(synced_ids)
                log.info("Synced %d cached events.", len(synced_ids))

            # Periodic housekeeping
            self._cache.cleanup(days=7)

    # ------------------------------------------------------------------
    # WebSocket message handler
    # ------------------------------------------------------------------

    async def _on_ws_message(self, msg: dict[str, Any]) -> None:
        """Handle an incoming WebSocket message from the backend."""
        msg_type = msg.get("type", "")

        if msg_type == "rule_update":
            rules = msg.get("rules", {})
            log.info("Received rule update via WebSocket.")
            self._apply_rules(rules)
            self._cache.cache_rules(rules)

        elif msg_type == "block_app":
            group_id = msg.get("app_group_id", "")
            log.info("WS: block_app group=%s", group_id)
            self._blocker.block_group(group_id)
            # Immediately enforce
            await self._blocker.enforce(self._monitor.current_session)

        elif msg_type == "unblock_app":
            group_id = msg.get("app_group_id", "")
            log.info("WS: unblock_app group=%s", group_id)
            self._blocker.unblock_group(group_id)

        elif msg_type == "tan_redeemed":
            log.info("WS: TAN redeemed — refreshing rules.")
            await self._fetch_and_cache_rules()

        elif msg_type in ("pong", "heartbeat_ack", "ack"):
            pass  # Expected responses — nothing to do

        else:
            log.debug("Unhandled WS message type: %s", msg_type)

    # ------------------------------------------------------------------
    # Block action callback (from AppBlocker)
    # ------------------------------------------------------------------

    def _on_block_action(self, executable: str, group_id: str) -> None:
        """Called when the blocker kills a process."""
        log.info("Blocked %s (group %s) — showing overlay.", executable, group_id)

        # Find group info for the overlay
        group_name = group_id
        used = 0
        limit = 0
        for gl in self._rules.get("group_limits", []):
            if gl.get("app_group_id") == group_id:
                group_name = gl.get("group_name", group_id)
                used = gl.get("used_minutes", 0)
                limit = gl.get("limit_minutes", 0)
                break

        self._overlay.show(executable, group_name, used, limit)

    # ------------------------------------------------------------------
    # TOTP callbacks (from overlay)
    # ------------------------------------------------------------------

    def _verify_totp_code_offline(self, code: str) -> bool:
        """Verify a 6-digit TOTP code against the cached secret."""
        if self._totp_config is None:
            log.debug("TOTP: no config cached, cannot verify offline.")
            return False
        secret = self._totp_config.get("secret")
        if not secret:
            return False
        try:
            import pyotp
            return pyotp.TOTP(secret).verify(code, valid_window=1)
        except Exception:
            log.exception("TOTP offline verification error")
            return False

    def _on_totp_entered(self, code: str) -> None:
        """Called when the user enters a TOTP code in the overlay dialog."""
        if not self._verify_totp_code_offline(code):
            log.warning("TOTP: invalid code entered.")
            # Show error in overlay (non-blocking message box)
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Ungültiger Code", "Der eingegebene Code ist ungültig.")
                root.destroy()
            except Exception:
                pass
            return

        totp_cfg = self._totp_config or {}
        mode = totp_cfg.get("mode", "tan")
        minutes = (
            totp_cfg.get("override_minutes", 30)
            if mode == "override"
            else totp_cfg.get("tan_minutes", 30)
        )

        log.info("TOTP: valid code — granting %d min (%s mode).", minutes, mode)

        # Apply local override: suspend enforcement for 'minutes' minutes
        self._totp_override_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

        # Unblock all currently blocked groups so the overlay can be dismissed
        for group_id in list(self._blocker.blocked_groups):
            self._blocker.unblock_group(group_id)
        self._overlay.dismiss()

        log.info("TOTP override active until %s.", self._totp_override_until.isoformat())

    # ------------------------------------------------------------------
    # TAN entry callback (from overlay)
    # ------------------------------------------------------------------

    def _on_tan_entered(self, tan_code: str) -> None:
        """Called when the user enters a TAN in the overlay dialog."""
        log.info("TAN entered: %s***", tan_code[:4] if len(tan_code) >= 4 else "?")
        # TAN redemption is handled by the parent portal or the child app,
        # not directly by the agent. Open the PWA for now.
        import webbrowser
        webbrowser.open(f"{self._config.server_url}/tans")

    # ------------------------------------------------------------------
    # Online / offline helpers
    # ------------------------------------------------------------------

    def _set_online(self) -> None:
        if not self._online:
            self._online = True
            self._tray.update_status("connected")
            log.info("Connection restored — agent is online.")

    def _set_offline(self) -> None:
        if self._online:
            self._online = False
            self._tray.update_status("offline")
            log.warning("Backend unreachable — agent is offline.")


# ---------------------------------------------------------------------------
# Console entry point
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)


def main() -> None:
    """CLI entry point for the Heimdall Windows Agent."""
    parser = argparse.ArgumentParser(description="Heimdall Windows Agent")
    parser.add_argument(
        "--register", action="store_true",
        help="Interaktive Geraeteregistrierung starten.",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Demo-Modus ohne Backend (fest verdrahtete Regeln).",
    )
    parser.add_argument(
        "--remote-control", action="store_true",
        help="HTTP-Fernbedienung aktivieren (default: Port 9876).",
    )
    parser.add_argument(
        "--remote-port", type=int, default=9876,
        help="Port fuer die Fernbedienung (default: 9876).",
    )
    parser.add_argument(
        "--service", action="store_true",
        help="Run as a Windows service (requires pywin32).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)

    if args.register:
        from .register import register_interactive
        register_interactive()
    elif args.demo:
        _run_demo(
            remote_control=args.remote_control,
            remote_port=args.remote_port,
            verbose=args.verbose,
        )
    elif args.service:
        _run_as_service()
    else:
        _run_console(
            remote_control=args.remote_control,
            remote_port=args.remote_port,
        )


def _run_console(
    remote_control: bool = False,
    remote_port: int = 9876,
) -> None:
    """Run the agent in console (foreground) mode."""
    config = AgentConfig.load()
    agent = HeimdallAgent(
        config,
        remote_control=remote_control,
        remote_port=remote_port,
    )
    _run_agent_loop(agent)


def _run_demo(
    remote_control: bool = False,
    remote_port: int = 9876,
    verbose: bool = False,
) -> None:
    """Run the agent in demo mode (no backend required)."""
    from .demo import create_demo_config

    config = create_demo_config()
    agent = HeimdallAgent(
        config,
        demo_mode=True,
        remote_control=remote_control,
        remote_port=remote_port,
    )
    _run_agent_loop(agent)


def _run_agent_loop(agent: HeimdallAgent) -> None:
    """Common event-loop setup for console and demo mode."""
    loop = asyncio.new_event_loop()

    # Handle Ctrl-C gracefully
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, agent._request_stop)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            signal.signal(sig, lambda s, f: agent._request_stop())

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        agent._request_stop()
        loop.run_until_complete(asyncio.sleep(0.5))
    finally:
        loop.close()


def _run_as_service() -> None:
    """Run the agent as a Windows service using pywin32.

    On non-Windows platforms this prints an error and exits.
    """
    if sys.platform != "win32":
        log.error("Windows service mode is only available on Windows.")
        sys.exit(1)

    try:
        import win32serviceutil  # type: ignore[import-untyped]
        import win32service  # type: ignore[import-untyped]
        import win32event  # type: ignore[import-untyped]
        import servicemanager  # type: ignore[import-untyped]
    except ImportError:
        log.error("pywin32 is required for service mode. Install it with: pip install pywin32")
        sys.exit(1)

    class HeimdallService(win32serviceutil.ServiceFramework):
        _svc_name_ = "HeimdallAgent"
        _svc_display_name_ = "Heimdall Device Agent"
        _svc_description_ = "Kindersicherungs-Agent — überwacht App-Nutzung und setzt Zeitregeln durch."

        def __init__(self, args: list[str]) -> None:
            win32serviceutil.ServiceFramework.__init__(self, args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._agent: HeimdallAgent | None = None

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._agent:
                self._agent._request_stop()
            win32event.SetEvent(self._stop_event)

        def SvcDoRun(self) -> None:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            config = AgentConfig.load()
            self._agent = HeimdallAgent(config)
            asyncio.run(self._agent.start())

    win32serviceutil.HandleCommandLine(HeimdallService)


if __name__ == "__main__":
    main()
