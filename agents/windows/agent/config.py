"""Agent configuration.

Loads settings from config.json on disk and environment variables.
The config file is stored next to the executable on first registration.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_SERVER = "http://localhost:8000"
_DEFAULT_API_PREFIX = "/api/v1"
_HEARTBEAT_INTERVAL = 60  # seconds
_RULE_POLL_INTERVAL = 300  # seconds (fallback when WS unavailable)
_MONITOR_INTERVAL = 2  # seconds between foreground-window checks


def _config_dir() -> Path:
    """Return the directory that stores persistent agent configuration."""
    if sys.platform == "win32":
        base = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
    else:
        base = Path.home() / ".config"
    d = base / "Heimdall"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class AgentConfig:
    """Runtime configuration for the Heimdall device agent."""

    server_url: str = _DEFAULT_SERVER
    api_prefix: str = _DEFAULT_API_PREFIX
    device_token: str = ""
    device_id: str = ""
    child_id: str = ""
    device_name: str = ""
    heartbeat_interval: int = _HEARTBEAT_INTERVAL
    rule_poll_interval: int = _RULE_POLL_INTERVAL
    monitor_interval: int = _MONITOR_INTERVAL
    # Maps executable name (lowercase) -> app_group_id
    app_group_map: dict[str, str] = field(default_factory=dict)

    @property
    def api_base(self) -> str:
        return f"{self.server_url}{self.api_prefix}"

    @property
    def ws_url(self) -> str:
        """WebSocket URL derived from server_url."""
        url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{url}{self.api_prefix}/agent/ws"

    @property
    def is_registered(self) -> bool:
        return bool(self.device_token)

    # -- Persistence ----------------------------------------------------------

    @classmethod
    def load(cls) -> AgentConfig:
        """Load config from disk, falling back to defaults + env vars."""
        cfg = cls()
        path = _config_dir() / "agent_config.json"

        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for key, val in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, val)

        # Environment overrides
        if env := os.environ.get("HEIMDALL_SERVER_URL"):
            cfg.server_url = env
        if env := os.environ.get("HEIMDALL_DEVICE_TOKEN"):
            cfg.device_token = env

        return cfg

    def save(self) -> None:
        """Persist current config to disk."""
        path = _config_dir() / "agent_config.json"
        data = {
            "server_url": self.server_url,
            "api_prefix": self.api_prefix,
            "device_token": self.device_token,
            "device_id": self.device_id,
            "child_id": self.child_id,
            "device_name": self.device_name,
            "heartbeat_interval": self.heartbeat_interval,
            "rule_poll_interval": self.rule_poll_interval,
            "monitor_interval": self.monitor_interval,
            "app_group_map": self.app_group_map,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
