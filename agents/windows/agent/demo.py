"""Demo mode configuration and data for testing without backend.

Provides hardcoded app-group mappings and rules so the agent can run
standalone on any Windows PC (or Linux dev machine) without a Heimdall
backend.
"""

from __future__ import annotations

import socket

from .config import AgentConfig

# ---------------------------------------------------------------------------
# Demo app groups — common Windows executables for easy testing
# ---------------------------------------------------------------------------

DEMO_APP_GROUPS: dict[str, list[str]] = {
    "gaming": [
        "notepad.exe",                          # easy to test on any PC
        "calc.exe",
        "CalculatorApp.exe",
        "Minecraft.Windows.exe",
        "FortniteClient-Win64-Shipping.exe",
    ],
    "browser": [
        "chrome.exe",
        "firefox.exe",
        "msedge.exe",
    ],
    "streaming": [
        "Spotify.exe",
        "vlc.exe",
    ],
    "productivity": [
        "WINWORD.EXE",
        "EXCEL.EXE",
        "POWERPNT.EXE",
        "Code.exe",
    ],
}

# Reverse mapping: executable (lowercase) -> group_id
DEMO_APP_GROUP_MAP: dict[str, str] = {
    exe.lower(): group_id
    for group_id, exes in DEMO_APP_GROUPS.items()
    for exe in exes
}

# ---------------------------------------------------------------------------
# Demo rules — realistic scenario with warning state on gaming
# ---------------------------------------------------------------------------

DEMO_RULES: dict = {
    "day_type": "weekday",
    "daily_limit_minutes": 120,
    "group_limits": [
        {
            "app_group_id": "gaming",
            "group_name": "Spiele",
            "limit_minutes": 60,
            "used_minutes": 45,  # 15 min left → warning state
        },
        {
            "app_group_id": "browser",
            "group_name": "Browser",
            "limit_minutes": 30,
            "used_minutes": 10,
        },
        {
            "app_group_id": "streaming",
            "group_name": "Streaming",
            "limit_minutes": 45,
            "used_minutes": 0,
        },
        {
            "app_group_id": "productivity",
            "group_name": "Produktivität",
            "limit_minutes": 999,
            "used_minutes": 0,
        },
    ],
    "time_windows": [],
    "active_tans": [],
}

# Pre-blocked groups in demo mode (gaming is already near limit)
DEMO_BLOCKED_GROUPS: list[str] = []


def create_demo_config() -> AgentConfig:
    """Create an AgentConfig suitable for demo mode (no backend)."""
    hostname = socket.gethostname()

    return AgentConfig(
        server_url="http://demo-mode",
        device_token="demo-token-12345",
        device_id="demo-device-id",
        child_id="demo-child-id",
        device_name=f"{hostname}-DEMO",
        app_group_map=DEMO_APP_GROUP_MAP,
    )


def get_demo_rules() -> dict:
    """Return a fresh copy of the demo rules dict."""
    import copy
    return copy.deepcopy(DEMO_RULES)
