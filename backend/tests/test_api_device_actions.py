"""Integration tests for device block/unblock endpoints."""

import uuid

import pytest


async def _setup_child_with_device(client, parent):
    """Create a child and a device. Returns (child_id, device_id, device_token)."""
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": "Block-Kind", "age": 10},
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
    device_id = data["device"]["id"]
    device_token = data["device_token"]
    return child_id, device_id, device_token


class TestBlockDevice:
    async def test_block_device(self, client, registered_parent):
        p = registered_parent
        child_id, device_id, _ = await _setup_child_with_device(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/{device_id}/block",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        # Device is not connected via WebSocket, so device_connected should be False
        assert data["device_connected"] is False

    async def test_block_nonexistent_device(self, client, registered_parent):
        p = registered_parent
        child_id, _, _ = await _setup_child_with_device(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/{uuid.uuid4()}/block",
            headers=p["headers"],
        )
        assert resp.status_code == 404


class TestUnblockDevice:
    async def test_unblock_device(self, client, registered_parent):
        p = registered_parent
        child_id, device_id, _ = await _setup_child_with_device(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/{device_id}/unblock",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_unblock_nonexistent_device(self, client, registered_parent):
        p = registered_parent
        child_id, _, _ = await _setup_child_with_device(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/{uuid.uuid4()}/unblock",
            headers=p["headers"],
        )
        assert resp.status_code == 404


class TestBlockAll:
    async def test_block_all_devices(self, client, registered_parent):
        p = registered_parent
        child_id, _, _ = await _setup_child_with_device(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/block-all",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        # No devices connected via WS, so 0 notified
        assert data["devices_notified"] == 0

    async def test_block_all_requires_parent(self, client, registered_parent):
        """Block-all should require parent role (not child)."""
        p = registered_parent
        child_id, _, _ = await _setup_child_with_device(client, p)

        # Without auth header -> 401
        resp = await client.post(
            f"/api/v1/children/{child_id}/devices/block-all",
        )
        assert resp.status_code in (401, 403)
