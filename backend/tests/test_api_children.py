"""Integration tests for the /api/v1/families/{family_id}/children endpoints."""

import uuid

import pytest
from tests.conftest import requires_pg


pytestmark = requires_pg


class TestCreateChild:
    async def test_create_child(self, client, registered_parent):
        p = registered_parent
        resp = await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Max", "age": 10},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Max"
        assert data["age"] == 10
        assert data["role"] == "child"
        assert data["family_id"] == p["family_id"]

    async def test_create_child_with_pin(self, client, registered_parent):
        p = registered_parent
        resp = await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Lisa", "age": 8, "pin": "1234"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Lisa"

    async def test_create_child_other_family_forbidden(self, client, registered_parent):
        p = registered_parent
        other_family_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/families/{other_family_id}/children/",
            headers=p["headers"],
            json={"name": "Kind", "age": 7},
        )
        assert resp.status_code == 403


class TestListChildren:
    async def test_list_children(self, client, registered_parent):
        p = registered_parent
        # Create two children
        await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Kind1", "age": 10},
        )
        await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Kind2", "age": 12},
        )

        resp = await client.get(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        children = resp.json()
        assert len(children) >= 2
        names = [c["name"] for c in children]
        assert "Kind1" in names
        assert "Kind2" in names


class TestGetChild:
    async def test_get_child(self, client, registered_parent):
        p = registered_parent
        create_resp = await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Einzelkind", "age": 9},
        )
        child_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/v1/families/{p['family_id']}/children/{child_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Einzelkind"

    async def test_get_nonexistent_child(self, client, registered_parent):
        p = registered_parent
        resp = await client.get(
            f"/api/v1/families/{p['family_id']}/children/{uuid.uuid4()}",
            headers=p["headers"],
        )
        assert resp.status_code == 404


class TestUpdateChild:
    async def test_update_child_name(self, client, registered_parent):
        p = registered_parent
        create_resp = await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Alt", "age": 10},
        )
        child_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/families/{p['family_id']}/children/{child_id}",
            headers=p["headers"],
            json={"name": "Neu", "age": 11},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neu"
        assert resp.json()["age"] == 11


class TestDeleteChild:
    async def test_delete_child(self, client, registered_parent):
        p = registered_parent
        create_resp = await client.post(
            f"/api/v1/families/{p['family_id']}/children/",
            headers=p["headers"],
            json={"name": "Entferntes Kind", "age": 5},
        )
        child_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/families/{p['family_id']}/children/{child_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 204

        # Verify child is gone
        resp2 = await client.get(
            f"/api/v1/families/{p['family_id']}/children/{child_id}",
            headers=p["headers"],
        )
        assert resp2.status_code == 404
