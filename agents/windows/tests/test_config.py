"""Tests for agent.config."""

from __future__ import annotations

import json
from pathlib import Path

from agent.config import AgentConfig


def test_default_config(config: AgentConfig) -> None:
    """Default values are set correctly."""
    assert config.server_url == "http://localhost:8000"
    assert config.api_prefix == "/api/v1"
    assert config.device_token == ""
    assert config.heartbeat_interval == 60
    assert config.monitor_interval == 2


def test_api_base(config: AgentConfig) -> None:
    """api_base combines server_url and api_prefix."""
    assert config.api_base == "http://localhost:8000/api/v1"


def test_ws_url(config: AgentConfig) -> None:
    """ws_url converts http to ws and appends the WS path."""
    assert config.ws_url == "ws://localhost:8000/api/v1/agent/ws"

    config.server_url = "https://heimdall.example.com"
    assert config.ws_url == "wss://heimdall.example.com/api/v1/agent/ws"


def test_is_registered(config: AgentConfig) -> None:
    """is_registered is True only when a device_token is set."""
    assert config.is_registered is False
    config.device_token = "tok_abc"
    assert config.is_registered is True


def test_save_and_load(tmp_config_dir: Path) -> None:
    """Roundtrip: save config, load it back, values match."""
    cfg = AgentConfig(
        server_url="http://example.com",
        device_token="my-token",
        device_id="dev-123",
        child_id="child-456",
        device_name="Test-PC",
    )
    cfg.save()

    loaded = AgentConfig.load()
    assert loaded.server_url == "http://example.com"
    assert loaded.device_token == "my-token"
    assert loaded.device_id == "dev-123"
    assert loaded.child_id == "child-456"
    assert loaded.device_name == "Test-PC"


def test_load_from_file(tmp_config_dir: Path) -> None:
    """Loading reads values from the JSON file on disk."""
    data = {
        "server_url": "http://test:9000",
        "device_token": "file-token",
        "heartbeat_interval": 30,
    }
    config_path = tmp_config_dir / "agent_config.json"
    config_path.write_text(json.dumps(data))

    cfg = AgentConfig.load()
    assert cfg.server_url == "http://test:9000"
    assert cfg.device_token == "file-token"
    assert cfg.heartbeat_interval == 30


def test_env_override(
    tmp_config_dir: Path, monkeypatch: "pytest.MonkeyPatch"
) -> None:
    """Environment variables override file-based config."""
    # Write a config file first
    cfg = AgentConfig(server_url="http://from-file", device_token="from-file")
    cfg.save()

    monkeypatch.setenv("HEIMDALL_SERVER_URL", "http://from-env")
    monkeypatch.setenv("HEIMDALL_DEVICE_TOKEN", "env-token")

    loaded = AgentConfig.load()
    assert loaded.server_url == "http://from-env"
    assert loaded.device_token == "env-token"
