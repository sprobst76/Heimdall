"""Tests for agent.blocker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.blocker import AppBlocker
from agent.config import AgentConfig
from agent.monitor import AppSession
from datetime import datetime, timezone


@pytest.fixture()
def blocker() -> AppBlocker:
    cfg = AgentConfig(
        app_group_map={
            "chrome.exe": "browser-group",
            "minecraft.exe": "games-group",
        }
    )
    return AppBlocker(cfg)


def _make_session(
    executable: str = "minecraft.exe",
    app_group_id: str | None = "games-group",
    pid: int = 1234,
) -> AppSession:
    return AppSession(
        executable=executable,
        window_title="Test",
        app_group_id=app_group_id,
        pid=pid,
        started_at=datetime.now(timezone.utc),
    )


def test_block_unblock_group(blocker: AppBlocker) -> None:
    """Blocking and unblocking modifies the blocked_groups set."""
    assert len(blocker.blocked_groups) == 0

    blocker.block_group("games-group")
    assert "games-group" in blocker.blocked_groups

    blocker.unblock_group("games-group")
    assert "games-group" not in blocker.blocked_groups


def test_is_blocked(blocker: AppBlocker) -> None:
    """is_blocked returns correct results for blocked, unblocked, and None groups."""
    blocker.block_group("games-group")

    assert blocker.is_blocked("games-group") is True
    assert blocker.is_blocked("browser-group") is False
    assert blocker.is_blocked(None) is False


@pytest.mark.asyncio
async def test_enforce_blocked_session(blocker: AppBlocker) -> None:
    """Enforcing a blocked session calls kill_by_executable."""
    blocker.block_group("games-group")
    session = _make_session()

    with patch.object(blocker, "kill_by_executable", return_value=1) as mock_kill:
        await blocker.enforce(session)
        mock_kill.assert_called_once_with("minecraft.exe")


@pytest.mark.asyncio
async def test_enforce_unblocked_session(blocker: AppBlocker) -> None:
    """Enforcing an unblocked session does nothing."""
    session = _make_session()

    with patch.object(blocker, "kill_by_executable") as mock_kill:
        await blocker.enforce(session)
        mock_kill.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_none_session(blocker: AppBlocker) -> None:
    """Enforcing None session is a no-op."""
    blocker.block_group("games-group")

    with patch.object(blocker, "kill_by_executable") as mock_kill:
        await blocker.enforce(None)
        mock_kill.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_fires_on_block_action(blocker: AppBlocker) -> None:
    """When on_block_action is set, it fires after killing a blocked app."""
    blocker.block_group("games-group")
    callback = MagicMock()
    blocker.on_block_action = callback
    session = _make_session()

    with patch.object(blocker, "kill_by_executable", return_value=1):
        await blocker.enforce(session)
        callback.assert_called_once_with("minecraft.exe", "games-group")
