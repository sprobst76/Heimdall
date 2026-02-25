"""Integration tests for POST /api/v1/agent/tamper-alert."""

import uuid
from datetime import datetime, timezone

import pytest


async def _setup_child_with_device(client, parent):
    """Create a child and a device. Returns (child_id, device_id, device_token)."""
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": "Tamper-Kind", "age": 10},
    )
    assert resp.status_code == 201
    child_id = resp.json()["id"]

    dev_resp = await client.post(
        f"/api/v1/children/{child_id}/devices/",
        headers=parent["headers"],
        json={
            "name": "Test Phone",
            "type": "android",
            "device_identifier": f"dev-{uuid.uuid4().hex[:8]}",
        },
    )
    assert dev_resp.status_code == 201
    data = dev_resp.json()
    return child_id, data["device"]["id"], data["device_token"]


class TestTamperAlert:
    async def test_tamper_alert_accepted(self, client, registered_parent):
        """Valid device token → 200 with status=received."""
        _, _, token = await _setup_child_with_device(client, registered_parent)

        resp = await client.post(
            "/api/v1/agent/tamper-alert",
            headers={"X-Device-Token": token},
            json={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "service_killed",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    async def test_tamper_alert_invalid_token(self, client):
        """Invalid token → 401."""
        resp = await client.post(
            "/api/v1/agent/tamper-alert",
            headers={"X-Device-Token": "invalid-token"},
            json={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "service_killed",
            },
        )
        assert resp.status_code == 401

    async def test_tamper_alert_missing_token(self, client):
        """Missing X-Device-Token header → 422."""
        resp = await client.post(
            "/api/v1/agent/tamper-alert",
            json={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "service_killed",
            },
        )
        assert resp.status_code == 422

    async def test_tamper_alert_custom_reason(self, client, registered_parent):
        """Different reason strings are all accepted."""
        _, _, token = await _setup_child_with_device(client, registered_parent)

        for reason in ("service_killed", "vpn_detected", "app_uninstalled"):
            resp = await client.post(
                "/api/v1/agent/tamper-alert",
                headers={"X-Device-Token": token},
                json={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": reason,
                },
            )
            assert resp.status_code == 200, f"Failed for reason={reason}"
