"""Test the health check endpoint."""


class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "Heimdall" in data["app"]
