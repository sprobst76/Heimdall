"""Integration tests for the /api/v1/children/{child_id}/tans endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest


async def _create_child(client, parent) -> str:
    """Helper: create a child and return its ID."""
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": "TAN-Kind", "age": 10},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestGenerateTAN:
    async def test_generate_time_tan(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        resp = await client.post(
            f"/api/v1/children/{child_id}/tans/generate",
            headers=p["headers"],
            json={
                "type": "time",
                "value_minutes": 30,
                "expires_at": expires,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "time"
        assert data["value_minutes"] == 30
        assert data["status"] == "active"
        assert data["source"] == "parent_manual"
        assert "-" in data["code"]  # WORD-NNNN format

    async def test_generate_tan_default_expiry(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/tans/generate",
            headers=p["headers"],
            json={"type": "time", "value_minutes": 15},
        )
        assert resp.status_code == 201
        assert resp.json()["expires_at"] is not None


class TestListTANs:
    async def test_list_tans(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        # Generate two TANs
        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        for minutes in (15, 30):
            await client.post(
                f"/api/v1/children/{child_id}/tans/generate",
                headers=p["headers"],
                json={"type": "time", "value_minutes": minutes, "expires_at": expires},
            )

        resp = await client.get(
            f"/api/v1/children/{child_id}/tans/",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        tans = resp.json()
        assert len(tans) >= 2

    async def test_list_tans_filter_status(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        await client.post(
            f"/api/v1/children/{child_id}/tans/generate",
            headers=p["headers"],
            json={"type": "time", "value_minutes": 10, "expires_at": expires},
        )

        resp = await client.get(
            f"/api/v1/children/{child_id}/tans/?status=active",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        for tan in resp.json():
            assert tan["status"] == "active"


class TestRedeemTAN:
    async def test_redeem_tan(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        gen_resp = await client.post(
            f"/api/v1/children/{child_id}/tans/generate",
            headers=p["headers"],
            json={"type": "time", "value_minutes": 20, "expires_at": expires},
        )
        code = gen_resp.json()["code"]

        resp = await client.post(
            f"/api/v1/children/{child_id}/tans/redeem",
            headers=p["headers"],
            json={"code": code},
        )
        # May fail during blackout hours (21:00-06:00 UTC)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "redeemed"
            assert data["redeemed_at"] is not None
        else:
            assert resp.status_code == 400
            assert "blackout" in resp.json()["detail"].lower()

    async def test_redeem_nonexistent_code(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/tans/redeem",
            headers=p["headers"],
            json={"code": "FAKE-0000"},
        )
        assert resp.status_code == 404


class TestInvalidateTAN:
    async def test_invalidate_tan(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        gen_resp = await client.post(
            f"/api/v1/children/{child_id}/tans/generate",
            headers=p["headers"],
            json={"type": "time", "value_minutes": 10, "expires_at": expires},
        )
        tan_id = gen_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/children/{child_id}/tans/{tan_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 204

    async def test_invalidate_nonexistent_tan(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        resp = await client.delete(
            f"/api/v1/children/{child_id}/tans/{uuid.uuid4()}",
            headers=p["headers"],
        )
        assert resp.status_code == 404
