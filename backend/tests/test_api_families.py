"""Integration tests for the /api/v1/families endpoints."""

import pytest
from tests.conftest import requires_pg


pytestmark = requires_pg


class TestGetFamily:
    async def test_get_own_family(self, client, registered_parent):
        p = registered_parent
        resp = await client.get(
            f"/api/v1/families/{p['family_id']}",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Familie"
        assert data["timezone"] == "Europe/Berlin"
        assert data["id"] == p["family_id"]

    async def test_get_other_family_forbidden(self, client, registered_parent):
        p = registered_parent
        # Random UUID that doesn't belong to this user
        import uuid

        other_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/families/{other_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 403

    async def test_get_family_unauthenticated(self, client, registered_parent):
        p = registered_parent
        resp = await client.get(f"/api/v1/families/{p['family_id']}")
        assert resp.status_code == 401


class TestUpdateFamily:
    async def test_update_family_name(self, client, registered_parent):
        p = registered_parent
        resp = await client.put(
            f"/api/v1/families/{p['family_id']}",
            headers=p["headers"],
            json={"name": "Neuer Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neuer Name"

    async def test_update_family_timezone(self, client, registered_parent):
        p = registered_parent
        resp = await client.put(
            f"/api/v1/families/{p['family_id']}",
            headers=p["headers"],
            json={"timezone": "Europe/Vienna"},
        )
        assert resp.status_code == 200
        assert resp.json()["timezone"] == "Europe/Vienna"


class TestListMembers:
    async def test_list_members(self, client, registered_parent):
        p = registered_parent
        resp = await client.get(
            f"/api/v1/families/{p['family_id']}/members",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) >= 1
        assert any(m["id"] == p["user_id"] for m in members)
