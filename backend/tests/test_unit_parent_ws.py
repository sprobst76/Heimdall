"""Tests for parent portal WebSocket and connection manager parent features."""

import uuid

import pytest

from app.services.connection_manager import ConnectionManager


class FakeWebSocket:
    """Minimal fake WebSocket for testing."""

    def __init__(self):
        self.sent: list[dict] = []
        self.closed = False

    async def send_json(self, data: dict):
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.sent.append(data)

    async def close(self, code: int = 1000):
        self.closed = True


class TestParentConnectionManager:
    async def test_connect_and_notify_parent(self):
        """Parent connects and receives notifications."""
        mgr = ConnectionManager()
        family_id = uuid.uuid4()
        ws = FakeWebSocket()

        await mgr.connect_parent(family_id, ws)
        count = await mgr.notify_parents(family_id, {"type": "invalidate", "keys": [["test"]]})

        assert count == 1
        assert len(ws.sent) == 1
        assert ws.sent[0]["type"] == "invalidate"

    async def test_disconnect_parent(self):
        """After disconnect, no more notifications."""
        mgr = ConnectionManager()
        family_id = uuid.uuid4()
        ws = FakeWebSocket()

        await mgr.connect_parent(family_id, ws)
        await mgr.disconnect_parent(family_id, ws)

        count = await mgr.notify_parents(family_id, {"type": "test"})
        assert count == 0

    async def test_multiple_parent_connections(self):
        """Multiple parent tabs receive notifications."""
        mgr = ConnectionManager()
        family_id = uuid.uuid4()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()

        await mgr.connect_parent(family_id, ws1)
        await mgr.connect_parent(family_id, ws2)

        count = await mgr.notify_parents(family_id, {"type": "invalidate", "keys": [["a"]]})

        assert count == 2
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

    async def test_notify_wrong_family(self):
        """Notifications only go to the correct family."""
        mgr = ConnectionManager()
        family_a = uuid.uuid4()
        family_b = uuid.uuid4()
        ws_a = FakeWebSocket()
        ws_b = FakeWebSocket()

        await mgr.connect_parent(family_a, ws_a)
        await mgr.connect_parent(family_b, ws_b)

        await mgr.notify_parents(family_a, {"type": "invalidate", "keys": [["a"]]})

        assert len(ws_a.sent) == 1
        assert len(ws_b.sent) == 0

    async def test_notify_handles_broken_connection(self):
        """Broken WebSocket doesn't crash notify_parents."""
        mgr = ConnectionManager()
        family_id = uuid.uuid4()
        ws_good = FakeWebSocket()
        ws_broken = FakeWebSocket()
        ws_broken.closed = True  # Simulate broken connection

        await mgr.connect_parent(family_id, ws_good)
        await mgr.connect_parent(family_id, ws_broken)

        count = await mgr.notify_parents(family_id, {"type": "test"})
        assert count == 1  # Only the good one
        assert len(ws_good.sent) == 1

    async def test_parent_and_device_connections_independent(self):
        """Parent connections don't interfere with device connections."""
        mgr = ConnectionManager()
        family_id = uuid.uuid4()
        device_id = uuid.uuid4()
        child_id = uuid.uuid4()
        ws_parent = FakeWebSocket()
        ws_device = FakeWebSocket()

        await mgr.connect_parent(family_id, ws_parent)
        await mgr.connect(device_id, child_id, ws_device)

        # Notify parents only
        await mgr.notify_parents(family_id, {"type": "invalidate"})
        assert len(ws_parent.sent) == 1
        assert len(ws_device.sent) == 0

        # Send to device only
        await mgr.send_to_device(device_id, {"type": "rules_updated"})
        assert len(ws_parent.sent) == 1
        assert len(ws_device.sent) == 1
