"""Tests for agent.communication (REST client only)."""

from __future__ import annotations

import httpx
import pytest

from agent.communication import RestClient
from agent.config import AgentConfig


def _make_config() -> AgentConfig:
    return AgentConfig(
        server_url="http://testserver",
        device_token="test-device-token",
    )


def _mock_transport(handler):
    """Create an httpx.MockTransport from a handler function."""
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_send_heartbeat() -> None:
    """send_heartbeat POSTs to /agent/heartbeat with the correct payload."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content
        return httpx.Response(200, json={"status": "ok"})

    config = _make_config()
    client = RestClient(config)
    # Inject mock transport
    client._client = httpx.AsyncClient(
        base_url=config.api_base,
        headers={"X-Device-Token": config.device_token},
        transport=httpx.MockTransport(handler),
    )

    result = await client.send_heartbeat(active_app="chrome.exe")

    assert result == {"status": "ok"}
    assert "/agent/heartbeat" in captured["url"]
    assert captured["headers"]["x-device-token"] == "test-device-token"
    await client.close()


@pytest.mark.asyncio
async def test_send_usage_event() -> None:
    """send_usage_event POSTs to /agent/usage-event with the correct payload."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"id": "evt-123"})

    config = _make_config()
    client = RestClient(config)
    client._client = httpx.AsyncClient(
        base_url=config.api_base,
        headers={"X-Device-Token": config.device_token},
        transport=httpx.MockTransport(handler),
    )

    result = await client.send_usage_event(
        app_package="minecraft.exe",
        app_group_id="games",
        event_type="start",
    )

    assert result["id"] == "evt-123"
    assert "/agent/usage-event" in captured["url"]
    await client.close()


@pytest.mark.asyncio
async def test_fetch_rules() -> None:
    """fetch_rules GETs /agent/rules/current."""
    rules_data = {
        "day_type": "school",
        "daily_limit_minutes": 120,
        "time_windows": [],
        "group_limits": [],
        "active_tans": [],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/agent/rules/current" in str(request.url)
        return httpx.Response(200, json=rules_data)

    config = _make_config()
    client = RestClient(config)
    client._client = httpx.AsyncClient(
        base_url=config.api_base,
        headers={"X-Device-Token": config.device_token},
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_rules()
    assert result["daily_limit_minutes"] == 120
    assert result["day_type"] == "school"
    await client.close()


@pytest.mark.asyncio
async def test_heartbeat_error_raises() -> None:
    """HTTP errors from the heartbeat endpoint are propagated."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    config = _make_config()
    client = RestClient(config)
    client._client = httpx.AsyncClient(
        base_url=config.api_base,
        headers={"X-Device-Token": config.device_token},
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.send_heartbeat()
    await client.close()
