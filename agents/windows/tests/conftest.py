"""Shared fixtures for the Heimdall agent test suite."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from agent.config import AgentConfig
from agent.offline_cache import OfflineCache


@pytest.fixture()
def tmp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override the config directory so tests never touch the real filesystem."""
    monkeypatch.setattr("agent.config._config_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture()
def config(tmp_config_dir: Path) -> AgentConfig:
    """Return a fresh AgentConfig with default values pointing at tmp_config_dir."""
    return AgentConfig()


@pytest.fixture()
def offline_cache(tmp_path: Path) -> OfflineCache:
    """Return an OfflineCache backed by a temporary SQLite file."""
    db_path = tmp_path / "test_cache.db"
    return OfflineCache(db_path=db_path)
