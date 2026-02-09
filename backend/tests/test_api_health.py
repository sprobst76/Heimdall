"""Test the health check endpoint (no DB required)."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")


@pytest_asyncio.fixture()
async def bare_client():
    """Client without DB override — only for endpoints that don't need DB."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    async def test_health_check(self, bare_client):
        resp = await bare_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "Heimdall" in data["app"]
