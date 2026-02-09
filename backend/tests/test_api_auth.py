"""Integration tests for the /api/v1/auth endpoints."""

import pytest
from tests.conftest import requires_pg


pytestmark = requires_pg


class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@test.de",
            "password": "testpassword123",
            "name": "Neuer Nutzer",
            "family_name": "Neue Familie",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client):
        payload = {
            "email": "dupe@test.de",
            "password": "testpassword123",
            "name": "Erster",
            "family_name": "Familie",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 200

        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_short_password(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "short@test.de",
            "password": "kurz",
            "name": "Test",
            "family_name": "Familie",
        })
        assert resp.status_code == 422  # validation error

    async def test_register_invalid_email(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "testpassword123",
            "name": "Test",
            "family_name": "Familie",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client):
        # Register first
        await client.post("/api/v1/auth/register", json={
            "email": "login@test.de",
            "password": "testpassword123",
            "name": "Login User",
            "family_name": "Familie",
        })

        resp = await client.post("/api/v1/auth/login", json={
            "email": "login@test.de",
            "password": "testpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@test.de",
            "password": "testpassword123",
            "name": "Test",
            "family_name": "Familie",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrongpw@test.de",
            "password": "falschespasswort",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "gibts-nicht@test.de",
            "password": "testpassword123",
        })
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "refresh@test.de",
            "password": "testpassword123",
            "name": "Refresh User",
            "family_name": "Familie",
        })
        tokens = reg.json()

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert "access_token" in new_tokens
        # Old refresh token should now be revoked
        assert new_tokens["access_token"] != tokens["access_token"]

    async def test_refresh_with_revoked_token(self, client):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "revoked@test.de",
            "password": "testpassword123",
            "name": "Revoked User",
            "family_name": "Familie",
        })
        tokens = reg.json()

        # Use the refresh token once (revokes it)
        await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })

        # Try to use it again — should fail
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 401

    async def test_refresh_with_invalid_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.string",
        })
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_revokes_token(self, client):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "logout@test.de",
            "password": "testpassword123",
            "name": "Logout User",
            "family_name": "Familie",
        })
        tokens = reg.json()

        resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 204

        # Refresh should fail now
        resp2 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp2.status_code == 401

    async def test_logout_with_unknown_token(self, client):
        """Logout with unknown token should still return 204 (idempotent)."""
        resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": "does.not.exist",
        })
        assert resp.status_code == 204
