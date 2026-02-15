"""HTTP-based remote control API for the Heimdall agent.

Provides a lightweight REST API that allows external tools (e.g. ``curl``
from a developer machine) to inspect and control the agent at runtime.
Useful for demo mode testing and debugging.

Start with ``--remote-control`` flag::

    python -m agent.main --demo --remote-control -v

Then from any machine on the LAN::

    curl http://<agent-ip>:9876/status
    curl -X POST http://<agent-ip>:9876/block -H 'Content-Type: application/json' -d '{"group_id":"gaming"}'
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from .main import HeimdallAgent

log = logging.getLogger(__name__)


class RemoteControlServer:
    """Embedded HTTP server for remote control of the agent."""

    def __init__(self, port: int, agent: HeimdallAgent) -> None:
        self._port = port
        self._agent = agent
        self._app = web.Application(middlewares=[self._error_middleware])
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        r = self._app.router
        r.add_get("/status", self._handle_status)
        r.add_get("/groups", self._handle_groups)
        r.add_post("/block", self._handle_block)
        r.add_post("/unblock", self._handle_unblock)
        r.add_post("/simulate/foreground", self._handle_simulate_foreground)
        r.add_post("/simulate/clear", self._handle_simulate_clear)
        r.add_post("/overlay/show", self._handle_overlay_show)
        r.add_post("/overlay/dismiss", self._handle_overlay_dismiss)
        r.add_post("/rules/update", self._handle_rules_update)

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    @web.middleware
    async def _error_middleware(
        self,
        request: web.Request,
        handler: Any,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON in request body"}, status=400,
            )
        except Exception as e:
            log.exception("Remote control error")
            return web.json_response(
                {"error": str(e)}, status=500,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the HTTP server and block until the agent stops."""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()

        log.info(
            "Remote control running on http://0.0.0.0:%d", self._port,
        )

        # Block until agent signals stop
        await self._agent._stop_event.wait()
        await self._runner.cleanup()

    # ------------------------------------------------------------------
    # GET /status
    # ------------------------------------------------------------------

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Return current agent state."""
        session = self._agent._monitor.current_session

        return web.json_response({
            "status": "running",
            "demo_mode": self._agent._demo_mode,
            "online": self._agent._online,
            "tray_status": self._agent._tray._status,
            "blocked_groups": sorted(self._agent._blocker.blocked_groups),
            "current_app": {
                "executable": session.executable,
                "window_title": session.window_title,
                "app_group_id": session.app_group_id,
                "pid": session.pid,
            } if session else None,
            "group_times": {
                name: {"used": used, "limit": limit}
                for name, (used, limit)
                in self._agent._tray._group_times.items()
            },
            "remote_port": self._port,
        })

    # ------------------------------------------------------------------
    # GET /groups
    # ------------------------------------------------------------------

    async def _handle_groups(self, request: web.Request) -> web.Response:
        """Return the current app-group mapping."""
        return web.json_response({
            "app_group_map": self._agent._config.app_group_map,
        })

    # ------------------------------------------------------------------
    # POST /block   {"group_id": "gaming"}
    # ------------------------------------------------------------------

    async def _handle_block(self, request: web.Request) -> web.Response:
        data = await request.json()
        group_id = data.get("group_id")
        if not group_id:
            return web.json_response(
                {"error": "group_id is required"}, status=400,
            )

        self._agent._blocker.block_group(group_id)
        log.info("Remote: blocked group %s", group_id)

        # Immediately enforce on current session
        await self._agent._blocker.enforce(
            self._agent._monitor.current_session,
        )

        return web.json_response({
            "ok": True,
            "action": "blocked",
            "group_id": group_id,
            "blocked_groups": sorted(self._agent._blocker.blocked_groups),
        })

    # ------------------------------------------------------------------
    # POST /unblock   {"group_id": "gaming"}
    # ------------------------------------------------------------------

    async def _handle_unblock(self, request: web.Request) -> web.Response:
        data = await request.json()
        group_id = data.get("group_id")
        if not group_id:
            return web.json_response(
                {"error": "group_id is required"}, status=400,
            )

        self._agent._blocker.unblock_group(group_id)
        log.info("Remote: unblocked group %s", group_id)

        # Update tray status
        if self._agent._blocker.blocked_groups:
            self._agent._tray.update_status("blocked")
        else:
            self._agent._tray.update_status("connected")

        return web.json_response({
            "ok": True,
            "action": "unblocked",
            "group_id": group_id,
            "blocked_groups": sorted(self._agent._blocker.blocked_groups),
        })

    # ------------------------------------------------------------------
    # POST /simulate/foreground   {"executable": "notepad.exe"}
    # ------------------------------------------------------------------

    async def _handle_simulate_foreground(
        self, request: web.Request,
    ) -> web.Response:
        data = await request.json()
        executable = data.get("executable")
        if not executable:
            return web.json_response(
                {"error": "executable is required"}, status=400,
            )

        window_title = data.get("window_title", f"Simulated: {executable}")
        self._agent._monitor.simulate_foreground(executable, window_title)
        log.info("Remote: simulating foreground %s", executable)

        # Trigger an immediate poll so the change is picked up
        await self._agent._monitor.poll()

        session = self._agent._monitor.current_session
        return web.json_response({
            "ok": True,
            "simulated": executable,
            "app_group_id": session.app_group_id if session else None,
            "is_blocked": (
                session.app_group_id in self._agent._blocker.blocked_groups
                if session and session.app_group_id
                else False
            ),
        })

    # ------------------------------------------------------------------
    # POST /simulate/clear
    # ------------------------------------------------------------------

    async def _handle_simulate_clear(
        self, request: web.Request,
    ) -> web.Response:
        self._agent._monitor.clear_simulation()
        log.info("Remote: cleared simulation")
        return web.json_response({"ok": True, "action": "simulation_cleared"})

    # ------------------------------------------------------------------
    # POST /overlay/show   {"app_name": "Notepad", "group_name": "Spiele", ...}
    # ------------------------------------------------------------------

    async def _handle_overlay_show(
        self, request: web.Request,
    ) -> web.Response:
        data = await request.json()
        app_name = data.get("app_name", "Test App")
        group_name = data.get("group_name", "Test Gruppe")
        used = data.get("used_minutes", 60)
        limit = data.get("limit_minutes", 60)

        self._agent._overlay.show(app_name, group_name, used, limit)
        log.info("Remote: showing overlay for %s", app_name)
        return web.json_response({"ok": True, "action": "overlay_shown"})

    # ------------------------------------------------------------------
    # POST /overlay/dismiss
    # ------------------------------------------------------------------

    async def _handle_overlay_dismiss(
        self, request: web.Request,
    ) -> web.Response:
        self._agent._overlay.dismiss()
        log.info("Remote: dismissed overlay")
        return web.json_response({"ok": True, "action": "overlay_dismissed"})

    # ------------------------------------------------------------------
    # POST /rules/update   {"group_limits": [...], ...}
    # ------------------------------------------------------------------

    async def _handle_rules_update(
        self, request: web.Request,
    ) -> web.Response:
        if not self._agent._demo_mode:
            return web.json_response(
                {"error": "rules/update only available in demo mode"},
                status=403,
            )

        data = await request.json()
        self._agent._apply_rules(data)
        log.info("Remote: updated rules")
        return web.json_response({"ok": True, "action": "rules_updated"})
