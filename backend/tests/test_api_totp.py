"""Integration tests for the TOTP endpoints.

Endpoints under /api/v1/children/{child_id}/totp/:
  POST   /setup      — parent sets up TOTP, returns secret + provisioning URI
  GET    /status     — parent reads TOTP config
  PUT    /settings   — parent updates mode / minutes
  DELETE /           — parent disables TOTP
  POST   /unlock     — child validates a 6-digit code
"""

import pyotp
import pytest


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTotpSetup:
    async def test_setup_returns_secret_and_uri(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent)
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "secret" in data
        assert data["provisioning_uri"].startswith("otpauth://totp/")

    async def test_setup_enables_totp(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="SetupKind1")
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        status_resp = await client.get(
            f"/api/v1/children/{child_id}/totp/status",
            headers=registered_parent["headers"],
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["enabled"] is True

    async def test_setup_default_mode_is_tan(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="SetupKind2")
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        status = (
            await client.get(
                f"/api/v1/children/{child_id}/totp/status",
                headers=registered_parent["headers"],
            )
        ).json()
        assert status["mode"] == "tan"
        assert status["tan_minutes"] == 30

    async def test_setup_cross_family_forbidden(self, client, registered_parent):
        """A parent from a different family must not set up TOTP for this child."""
        other_reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other-totp@test.de",
                "password": "testpassword123",
                "name": "Anderer Elternteil",
                "family_name": "Andere Familie TOTP",
            },
        )
        other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}

        child_id = await _create_child(client, registered_parent, name="CrossKind")
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_setup_without_auth_is_unauthorized(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="NoAuthKind")
        resp = await client.post(f"/api/v1/children/{child_id}/totp/setup")
        assert resp.status_code == 401


class TestTotpSettings:
    async def test_update_mode_to_override(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="SettingsKind1")
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        resp = await client.put(
            f"/api/v1/children/{child_id}/totp/settings",
            headers=registered_parent["headers"],
            json={"mode": "override", "override_minutes": 60},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "override"
        assert data["override_minutes"] == 60

    async def test_update_tan_minutes(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="SettingsKind2")
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        resp = await client.put(
            f"/api/v1/children/{child_id}/totp/settings",
            headers=registered_parent["headers"],
            json={"tan_minutes": 45},
        )
        assert resp.status_code == 200
        assert resp.json()["tan_minutes"] == 45


class TestTotpDisable:
    async def test_disable_clears_secret(self, client, registered_parent):
        child_id = await _create_child(client, registered_parent, name="DisableKind")
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        del_resp = await client.delete(
            f"/api/v1/children/{child_id}/totp",
            headers=registered_parent["headers"],
        )
        assert del_resp.status_code == 204

        status_resp = await client.get(
            f"/api/v1/children/{child_id}/totp/status",
            headers=registered_parent["headers"],
        )
        assert status_resp.json()["enabled"] is False

    async def test_disable_nonexistent_child_is_404(self, client, registered_parent):
        import uuid
        resp = await client.delete(
            f"/api/v1/children/{uuid.uuid4()}/totp",
            headers=registered_parent["headers"],
        )
        assert resp.status_code == 404


class TestTotpUnlock:
    async def test_unlock_with_valid_code_tan_mode(self, client, registered_parent):
        child_id = await _create_child(
            client, registered_parent, name="UnlockKind1", pin="5678"
        )
        setup_resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        secret = setup_resp.json()["secret"]
        code = pyotp.TOTP(secret).now()

        child_hdrs = await _child_headers(client, "UnlockKind1", registered_parent["family_name"], "5678")
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=child_hdrs,
            json={"code": code, "mode": "tan"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["unlocked"] is True
        assert data["mode"] == "tan"
        assert data["minutes"] == 30  # default tan_minutes

    async def test_unlock_creates_active_tan(self, client, registered_parent):
        """After a successful unlock, an active TAN with source='totp' must exist."""
        child_id = await _create_child(
            client, registered_parent, name="UnlockKind2", pin="6789"
        )
        setup_resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        secret = setup_resp.json()["secret"]
        code = pyotp.TOTP(secret).now()

        child_hdrs = await _child_headers(client, "UnlockKind2", registered_parent["family_name"], "6789")
        await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=child_hdrs,
            json={"code": code, "mode": "tan"},
        )

        tans = (
            await client.get(
                f"/api/v1/children/{child_id}/tans/",
                headers=registered_parent["headers"],
            )
        ).json()
        assert any(t["source"] == "totp" for t in tans)

    async def test_unlock_invalid_code_returns_400(self, client, registered_parent):
        child_id = await _create_child(
            client, registered_parent, name="InvalidCodeKind", pin="9999"
        )
        await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        child_hdrs = await _child_headers(client, "InvalidCodeKind", registered_parent["family_name"], "9999")
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=child_hdrs,
            json={"code": "999999", "mode": "tan"},
        )
        assert resp.status_code == 400
        assert "Ungültiger Code" in resp.json()["detail"]

    async def test_unlock_totp_disabled_returns_400(self, client, registered_parent):
        """Attempting to unlock when TOTP is not set up must fail."""
        child_id = await _create_child(
            client, registered_parent, name="NoTotpKind", pin="1111"
        )
        child_hdrs = await _child_headers(client, "NoTotpKind", registered_parent["family_name"], "1111")
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=child_hdrs,
            json={"code": "123456", "mode": "tan"},
        )
        assert resp.status_code == 400

    async def test_unlock_wrong_mode_returns_400(self, client, registered_parent):
        """Requesting 'override' mode when only 'tan' is configured must fail."""
        child_id = await _create_child(
            client, registered_parent, name="WrongModeKind", pin="2222"
        )
        setup_resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        # Ensure mode is 'tan' (default)
        await client.put(
            f"/api/v1/children/{child_id}/totp/settings",
            headers=registered_parent["headers"],
            json={"mode": "tan"},
        )
        code = pyotp.TOTP(setup_resp.json()["secret"]).now()

        child_hdrs = await _child_headers(client, "WrongModeKind", registered_parent["family_name"], "2222")
        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=child_hdrs,
            json={"code": code, "mode": "override"},
        )
        assert resp.status_code == 400

    async def test_parent_cannot_call_unlock(self, client, registered_parent):
        """The /unlock endpoint requires child role, not parent."""
        child_id = await _create_child(
            client, registered_parent, name="ParentUnlockKind", pin="3333"
        )
        setup_resp = await client.post(
            f"/api/v1/children/{child_id}/totp/setup",
            headers=registered_parent["headers"],
        )
        code = pyotp.TOTP(setup_resp.json()["secret"]).now()

        resp = await client.post(
            f"/api/v1/children/{child_id}/totp/unlock",
            headers=registered_parent["headers"],
            json={"code": code, "mode": "tan"},
        )
        # Parent is not a child → 403
        assert resp.status_code == 403
