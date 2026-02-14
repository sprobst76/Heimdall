"""Tests for agent.monitor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from agent.config import AgentConfig
from agent.monitor import AppSession, ProcessMonitor


def test_get_foreground_app_dummy() -> None:
    """On non-Windows platforms the dummy fallback returns a stable tuple."""
    result = ProcessMonitor.get_foreground_app()
    assert result is not None
    exe, title, pid = result
    assert exe == "dummy.exe"
    assert isinstance(title, str)
    assert isinstance(pid, int)


def test_map_to_group() -> None:
    """Executable names are mapped to app_group_ids via config (case-insensitive)."""
    cfg = AgentConfig(
        app_group_map={
            "chrome.exe": "browser-group",
            "minecraft.exe": "games-group",
        }
    )
    monitor = ProcessMonitor(cfg, on_app_change=AsyncMock())

    assert monitor._map_to_group("chrome.exe") == "browser-group"
    assert monitor._map_to_group("Chrome.EXE") == "browser-group"
    assert monitor._map_to_group("notepad.exe") is None


@pytest.mark.asyncio
async def test_poll_detects_change() -> None:
    """When the foreground app changes, the on_app_change callback fires."""
    callback = AsyncMock()
    cfg = AgentConfig()
    monitor = ProcessMonitor(cfg, on_app_change=callback)

    # First poll — detects initial app
    await monitor.poll()
    assert callback.call_count == 1
    old, new = callback.call_args[0]
    assert old is None  # no previous session
    assert new is not None
    assert new.executable == "dummy.exe"


@pytest.mark.asyncio
async def test_poll_same_app_no_callback() -> None:
    """Polling again with the same app does NOT trigger the callback a second time."""
    callback = AsyncMock()
    cfg = AgentConfig()
    monitor = ProcessMonitor(cfg, on_app_change=callback)

    await monitor.poll()
    assert callback.call_count == 1

    # Second poll — same dummy app
    await monitor.poll()
    assert callback.call_count == 1  # no additional call


@pytest.mark.asyncio
async def test_current_session_tracks_state() -> None:
    """After a poll, current_session reflects the detected app."""
    cfg = AgentConfig()
    monitor = ProcessMonitor(cfg, on_app_change=AsyncMock())

    assert monitor.current_session is None
    await monitor.poll()
    assert monitor.current_session is not None
    assert monitor.current_session.executable == "dummy.exe"
