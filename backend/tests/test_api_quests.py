"""Integration tests for the quest endpoints.

Template CRUD:  /api/v1/families/{family_id}/quests
Instances:      /api/v1/children/{child_id}/quests
Lifecycle:      assign → claim → proof → review
"""

import pytest


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------

_TEMPLATE_BASE = {
    "name": "Zimmer aufräumen",
    "category": "haushalt",
    "reward_minutes": 30,
    "proof_type": "parent_confirm",
    "recurrence": "daily",
}


async def _create_child(client, parent, name: str = "Testkind", pin: str = "1234") -> str:
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/children/",
        headers=parent["headers"],
        json={"name": name, "age": 10, "pin": pin},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _child_headers(client, child_name: str, family_name: str, pin: str = "1234") -> dict:
    resp = await client.post(
        "/api/v1/auth/login-pin",
        json={"child_name": child_name, "family_name": family_name, "pin": pin},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_template(client, parent, name: str = "Zimmer aufräumen") -> dict:
    resp = await client.post(
        f"/api/v1/families/{parent['family_id']}/quests",
        headers=parent["headers"],
        json={**_TEMPLATE_BASE, "name": name},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuestTemplates:
    async def test_create_template_returns_201(self, client, registered_parent):
        resp = await client.post(
            f"/api/v1/families/{registered_parent['family_id']}/quests",
            headers=registered_parent["headers"],
            json=_TEMPLATE_BASE,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == _TEMPLATE_BASE["name"]
        assert data["reward_minutes"] == _TEMPLATE_BASE["reward_minutes"]
        assert data["category"] == _TEMPLATE_BASE["category"]

    async def test_list_templates_includes_created(self, client, registered_parent):
        tmpl = await _create_template(client, registered_parent, name="ListTestQuest")
        resp = await client.get(
            f"/api/v1/families/{registered_parent['family_id']}/quests",
            headers=registered_parent["headers"],
        )
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert tmpl["id"] in ids

    async def test_create_template_requires_parent(self, client, registered_parent):
        """Child token must not be able to create templates."""
        await _create_child(client, registered_parent, name="TemplateChildAuth", pin="0001")
        child_hdrs = await _child_headers(
            client, "TemplateChildAuth", registered_parent["family_name"], "0001"
        )
        resp = await client.post(
            f"/api/v1/families/{registered_parent['family_id']}/quests",
            headers=child_hdrs,
            json=_TEMPLATE_BASE,
        )
        assert resp.status_code == 403

    async def test_cross_family_template_forbidden(self, client, registered_parent):
        other = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other-quest@test.de",
                "password": "testpassword123",
                "name": "Anderer",
                "family_name": "Andere Familie Quest",
            },
        )
        other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
        resp = await client.post(
            f"/api/v1/families/{registered_parent['family_id']}/quests",
            headers=other_headers,
            json=_TEMPLATE_BASE,
        )
        assert resp.status_code == 403


class TestQuestInstances:
    async def test_parent_assigns_quest_to_child(self, client, registered_parent):
        tmpl = await _create_template(client, registered_parent, name="AssignQuest")
        child_id = await _create_child(client, registered_parent, name="AssignKind", pin="0002")

        resp = await client.post(
            f"/api/v1/children/{child_id}/quests/assign?template_id={tmpl['id']}",
            headers=registered_parent["headers"],
        )
        assert resp.status_code == 201
        instance = resp.json()
        assert instance["template_id"] == tmpl["id"]
        assert instance["status"] == "available"

    async def test_child_sees_assigned_quest(self, client, registered_parent):
        tmpl = await _create_template(client, registered_parent, name="VisibleQuest")
        child_id = await _create_child(client, registered_parent, name="VisibleKind", pin="0003")

        await client.post(
            f"/api/v1/children/{child_id}/quests/assign?template_id={tmpl['id']}",
            headers=registered_parent["headers"],
        )

        child_hdrs = await _child_headers(client, "VisibleKind", registered_parent["family_name"], "0003")
        resp = await client.get(
            f"/api/v1/children/{child_id}/quests",
            headers=child_hdrs,
        )
        assert resp.status_code == 200
        template_ids = [q["template_id"] for q in resp.json()]
        assert tmpl["id"] in template_ids

    async def test_child_claims_quest(self, client, registered_parent):
        tmpl = await _create_template(client, registered_parent, name="ClaimQuest")
        child_id = await _create_child(client, registered_parent, name="ClaimKind", pin="0004")

        instance = (
            await client.post(
                f"/api/v1/children/{child_id}/quests/assign?template_id={tmpl['id']}",
                headers=registered_parent["headers"],
            )
        ).json()

        child_hdrs = await _child_headers(client, "ClaimKind", registered_parent["family_name"], "0004")
        claim_resp = await client.post(
            f"/api/v1/children/{child_id}/quests/{instance['id']}/claim",
            headers=child_hdrs,
        )
        assert claim_resp.status_code == 200
        assert claim_resp.json()["status"] == "claimed"

    async def test_assign_inactive_template_fails(self, client, registered_parent):
        tmpl = await _create_template(client, registered_parent, name="InactiveQuest")
        # Deactivate template
        await client.put(
            f"/api/v1/families/{registered_parent['family_id']}/quests/{tmpl['id']}",
            headers=registered_parent["headers"],
            json={"active": False},
        )
        child_id = await _create_child(client, registered_parent, name="InactiveKind", pin="0005")
        resp = await client.post(
            f"/api/v1/children/{child_id}/quests/assign?template_id={tmpl['id']}",
            headers=registered_parent["headers"],
        )
        assert resp.status_code == 404


class TestQuestApproval:
    async def _full_lifecycle(self, client, registered_parent, child_name: str, pin: str):
        """Helper: create template, assign, claim, submit proof. Returns (child_id, instance_id)."""
        tmpl = await _create_template(client, registered_parent, name=f"Quest für {child_name}")
        child_id = await _create_child(client, registered_parent, name=child_name, pin=pin)

        instance = (
            await client.post(
                f"/api/v1/children/{child_id}/quests/assign?template_id={tmpl['id']}",
                headers=registered_parent["headers"],
            )
        ).json()
        instance_id = instance["id"]

        child_hdrs = await _child_headers(client, child_name, registered_parent["family_name"], pin)
        await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/claim",
            headers=child_hdrs,
        )
        await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/proof",
            headers=child_hdrs,
            json={"proof_type": "parent_confirm", "proof_url": ""},
        )
        return child_id, instance_id, child_hdrs

    async def test_approve_sets_status_approved(self, client, registered_parent):
        child_id, instance_id, _ = await self._full_lifecycle(
            client, registered_parent, "ApproveKind", "0006"
        )
        resp = await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/review",
            headers=registered_parent["headers"],
            json={"approved": True, "feedback": None},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    async def test_approve_creates_quest_tan(self, client, registered_parent):
        """After approval, a TAN with source='quest' must be created."""
        child_id, instance_id, _ = await self._full_lifecycle(
            client, registered_parent, "TanQuestKind", "0007"
        )
        await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/review",
            headers=registered_parent["headers"],
            json={"approved": True, "feedback": None},
        )
        tans = (
            await client.get(
                f"/api/v1/children/{child_id}/tans/",
                headers=registered_parent["headers"],
            )
        ).json()
        assert any(t["source"] == "quest" for t in tans), (
            f"No quest TAN found. TANs: {tans}"
        )

    async def test_reject_sets_status_rejected(self, client, registered_parent):
        child_id, instance_id, _ = await self._full_lifecycle(
            client, registered_parent, "RejectKind", "0008"
        )
        resp = await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/review",
            headers=registered_parent["headers"],
            json={"approved": False, "feedback": "Nicht gut genug"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    async def test_reject_does_not_create_tan(self, client, registered_parent):
        child_id, instance_id, _ = await self._full_lifecycle(
            client, registered_parent, "RejectNoTanKind", "0009"
        )
        await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/review",
            headers=registered_parent["headers"],
            json={"approved": False, "feedback": "Nein"},
        )
        tans = (
            await client.get(
                f"/api/v1/children/{child_id}/tans/",
                headers=registered_parent["headers"],
            )
        ).json()
        assert not any(t["source"] == "quest" for t in tans)

    async def test_quest_stats_after_approval(self, client, registered_parent):
        """Quest stats endpoint must return completed_today >= 1 after approval."""
        child_id, instance_id, child_hdrs = await self._full_lifecycle(
            client, registered_parent, "StatsKind", "0010"
        )
        await client.post(
            f"/api/v1/children/{child_id}/quests/{instance_id}/review",
            headers=registered_parent["headers"],
            json={"approved": True, "feedback": None},
        )
        stats_resp = await client.get(
            f"/api/v1/children/{child_id}/quests/stats",
            headers=registered_parent["headers"],
        )
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats.get("completed_today", 0) >= 1
