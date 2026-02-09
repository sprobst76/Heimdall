"""Integration tests for the /api/v1/children/{child_id}/app-groups endpoints."""

import uuid

import pytest


async def _create_child(client, parent) -> str:
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": "AppGroup-Kind", "age": 10},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestAppGroupCRUD:
    async def test_create_app_group(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
            json={
                "name": "Spiele",
                "category": "gaming",
                "risk_level": "high",
                "icon": "🎮",
                "color": "#FF0000",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Spiele"
        assert data["category"] == "gaming"
        assert data["risk_level"] == "high"

    async def test_list_app_groups(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        for name in ("Lernen", "Social Media"):
            await client.post(
                f"/api/v1/children/{child_id}/app-groups/",
                headers=p["headers"],
                json={"name": name, "category": "education"},
            )

        resp = await client.get(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        groups = resp.json()
        names = [g["name"] for g in groups]
        assert "Lernen" in names
        assert "Social Media" in names

    async def test_update_app_group(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        create_resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
            json={"name": "Alt", "category": "misc"},
        )
        group_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/children/{child_id}/app-groups/{group_id}",
            headers=p["headers"],
            json={"name": "Neu", "always_allowed": True},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neu"
        assert resp.json()["always_allowed"] is True

    async def test_delete_app_group(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        create_resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
            json={"name": "Temp", "category": "misc"},
        )
        group_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/children/{child_id}/app-groups/{group_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 204


class TestAppGroupApps:
    async def test_add_app_to_group(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        group_resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
            json={"name": "Spiele", "category": "gaming"},
        )
        group_id = group_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/{group_id}/apps",
            headers=p["headers"],
            json={
                "app_name": "Minecraft",
                "app_package": "com.mojang.minecraftpe",
                "platform": "android",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["app_name"] == "Minecraft"

    async def test_list_apps_in_group(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        group_resp = await client.post(
            f"/api/v1/children/{child_id}/app-groups/",
            headers=p["headers"],
            json={"name": "Social", "category": "social"},
        )
        group_id = group_resp.json()["id"]

        # Add two apps
        for app_name, pkg in [("TikTok", "com.tiktok"), ("Instagram", "com.instagram")]:
            await client.post(
                f"/api/v1/children/{child_id}/app-groups/{group_id}/apps",
                headers=p["headers"],
                json={"app_name": app_name, "app_package": pkg, "platform": "android"},
            )

        # Apps are returned as part of the group response
        resp = await client.get(
            f"/api/v1/children/{child_id}/app-groups/{group_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        apps = resp.json()["apps"]
        assert len(apps) >= 2
        names = [a["app_name"] for a in apps]
        assert "TikTok" in names
        assert "Instagram" in names
