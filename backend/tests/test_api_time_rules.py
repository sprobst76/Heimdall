"""Integration tests for the /api/v1/children/{child_id}/time-rules endpoints."""

import uuid

import pytest


async def _create_child(client, parent) -> str:
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": "Regel-Kind", "age": 11},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestTimeRuleCRUD:
    async def test_create_time_rule(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        resp = await client.post(
            f"/api/v1/children/{child_id}/rules/",
            headers=p["headers"],
            json={
                "name": "Wochentag-Regel",
                "target_type": "device",
                "day_types": ["weekday"],
                "time_windows": [{"start": "14:00", "end": "18:00"}],
                "daily_limit_minutes": 120,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Wochentag-Regel"
        assert data["daily_limit_minutes"] == 120
        assert data["active"] is True

    async def test_list_time_rules(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        # Create two rules
        for name in ("Regel-A", "Regel-B"):
            await client.post(
                f"/api/v1/children/{child_id}/rules/",
                headers=p["headers"],
                json={
                    "name": name,
                    "target_type": "device",
                    "day_types": ["weekday"],
                    "time_windows": [{"start": "08:00", "end": "20:00"}],
                    "daily_limit_minutes": 60,
                },
            )

        resp = await client.get(
            f"/api/v1/children/{child_id}/rules/",
            headers=p["headers"],
        )
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) >= 2

    async def test_update_time_rule(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        create_resp = await client.post(
            f"/api/v1/children/{child_id}/rules/",
            headers=p["headers"],
            json={
                "name": "Update-Regel",
                "target_type": "device",
                "day_types": ["weekday"],
                "time_windows": [{"start": "14:00", "end": "18:00"}],
                "daily_limit_minutes": 90,
            },
        )
        rule_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/children/{child_id}/rules/{rule_id}",
            headers=p["headers"],
            json={"daily_limit_minutes": 150, "active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["daily_limit_minutes"] == 150
        assert resp.json()["active"] is False

    async def test_delete_time_rule(self, client, registered_parent):
        p = registered_parent
        child_id = await _create_child(client, p)

        create_resp = await client.post(
            f"/api/v1/children/{child_id}/rules/",
            headers=p["headers"],
            json={
                "name": "Lösch-Regel",
                "target_type": "device",
                "day_types": ["weekend"],
                "time_windows": [],
                "daily_limit_minutes": 180,
            },
        )
        rule_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/children/{child_id}/rules/{rule_id}",
            headers=p["headers"],
        )
        assert resp.status_code == 204
