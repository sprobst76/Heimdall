"""Process blocking module.

Finds and terminates processes whose app-group has exceeded its time
limit.  Uses a graceful ``terminate`` first, falling back to a hard
``kill`` after a configurable timeout.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

import psutil

if TYPE_CHECKING:
    from .monitor import AppSession

from .config import AgentConfig

log = logging.getLogger(__name__)


class AppBlocker:
    """Manages the set of blocked app-groups and enforces blocks by
    terminating matching processes.

    Parameters
    ----------
    config:
        The shared agent configuration.  ``config.app_group_map`` is
        consulted to resolve executable names to group IDs.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self.blocked_groups: set[str] = set()
        self.on_block_action: Callable[[str, str], None] | None = None

    # -- group management -----------------------------------------------------

    def block_group(self, group_id: str) -> None:
        """Mark *group_id* as blocked.  New and running sessions in this
        group will be terminated on the next :meth:`enforce` cycle."""
        if group_id not in self.blocked_groups:
            log.info("Blocking app group %s", group_id)
        self.blocked_groups.add(group_id)

    def unblock_group(self, group_id: str) -> None:
        """Remove *group_id* from the blocked set."""
        self.blocked_groups.discard(group_id)
        log.info("Unblocked app group %s", group_id)

    def is_blocked(self, app_group_id: str | None) -> bool:
        """Return ``True`` if *app_group_id* is currently blocked.

        An ``app_group_id`` of ``None`` (i.e. an untracked executable)
        is never considered blocked.
        """
        if app_group_id is None:
            return False
        return app_group_id in self.blocked_groups

    # -- process termination --------------------------------------------------

    def kill_process(self, pid: int, graceful_timeout: float = 3.0) -> bool:
        """Terminate a single process identified by *pid*.

        The process is first sent a ``SIGTERM`` (``terminate``).  If it
        is still alive after *graceful_timeout* seconds it is forcefully
        killed.

        Returns ``True`` if the process was successfully killed (or had
        already exited), ``False`` on failure.
        """
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            log.debug("PID %d no longer exists.", pid)
            return True

        exe_name = proc.name()
        log.info("Gracefully terminating PID %d (%s)...", pid, exe_name)

        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            log.warning("Cannot terminate PID %d: %s", pid, exc)
            return False

        try:
            proc.wait(timeout=graceful_timeout)
            log.info("PID %d terminated gracefully.", pid)
            return True
        except psutil.TimeoutExpired:
            pass

        # Graceful timeout elapsed -- force kill.
        log.warning("PID %d did not exit in %.1fs, force-killing.", pid, graceful_timeout)
        try:
            proc.kill()
            proc.wait(timeout=2.0)
            log.info("PID %d force-killed.", pid)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as exc:
            log.error("Failed to force-kill PID %d: %s", pid, exc)
            return False

    def kill_by_executable(self, executable: str) -> int:
        """Kill every running process whose name matches *executable*
        (case-insensitive comparison).

        Returns the number of processes successfully terminated.
        """
        killed = 0
        target = executable.lower()

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target:
                    if self.kill_process(proc.info["pid"]):
                        killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            log.info("Killed %d process(es) matching '%s'.", killed, executable)
        return killed

    # -- enforcement loop -----------------------------------------------------

    async def enforce(self, session: AppSession | None) -> None:
        """Check the current *session* and kill it if its app-group is
        blocked.

        This is meant to be called periodically from the monitor loop.
        If *session* is ``None`` or its group is not blocked, this
        method is a no-op.

        When a process is killed the optional :attr:`on_block_action`
        callback is invoked with ``(executable, group_id)`` so that the
        overlay can be displayed.
        """
        if session is None:
            return

        group_id = session.app_group_id
        if not self.is_blocked(group_id):
            return

        executable = session.executable
        log.info(
            "Session '%s' (group %s) is blocked -- killing process.",
            executable,
            group_id,
        )

        # Run the potentially blocking kill in a thread so we don't stall
        # the async event-loop.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.kill_by_executable, executable)

        if self.on_block_action is not None:
            try:
                self.on_block_action(executable, group_id)
            except Exception:
                log.exception("on_block_action callback failed")
