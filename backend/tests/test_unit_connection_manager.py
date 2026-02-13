"""Unit tests for ConnectionManager."""

import uuid

import pytest
from unittest.mock import AsyncMock

from app.services.connection_manager import ConnectionManager


class TestConnectionManager:
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        device_id = uuid.uuid4()
        child_id = uuid.uuid4()
        ws = AsyncMock()

        await manager.connect(device_id, child_id, ws)
        assert await manager.is_connected(device_id)
        assert await manager.get_connected_count(child_id) == 1

        await manager.disconnect(device_id, child_id)
        assert not await manager.is_connected(device_id)
        assert await manager.get_connected_count(child_id) == 0

    async def test_send_to_device(self):
        manager = ConnectionManager()
        device_id = uuid.uuid4()
        child_id = uuid.uuid4()
        ws = AsyncMock()

        await manager.connect(device_id, child_id, ws)

        message = {"type": "test", "data": "hello"}
        result = await manager.send_to_device(device_id, message)

        assert result is True
        ws.send_json.assert_called_once_with(message)

    async def test_send_to_disconnected_device(self):
        manager = ConnectionManager()
        device_id = uuid.uuid4()

        result = await manager.send_to_device(device_id, {"type": "test"})
        assert result is False

    async def test_send_to_child_devices(self):
        manager = ConnectionManager()
        child_id = uuid.uuid4()
        d1 = uuid.uuid4()
        d2 = uuid.uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(d1, child_id, ws1)
        await manager.connect(d2, child_id, ws2)

        message = {"type": "broadcast"}
        count = await manager.send_to_child_devices(child_id, message)

        assert count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    async def test_disconnect_cleans_up_child_devices(self):
        manager = ConnectionManager()
        child_id = uuid.uuid4()
        d1 = uuid.uuid4()
        d2 = uuid.uuid4()

        await manager.connect(d1, child_id, AsyncMock())
        await manager.connect(d2, child_id, AsyncMock())
        assert await manager.get_connected_count(child_id) == 2

        await manager.disconnect(d1, child_id)
        assert await manager.get_connected_count(child_id) == 1

        await manager.disconnect(d2, child_id)
        assert await manager.get_connected_count(child_id) == 0
        # Internal dict should be cleaned up
        assert child_id not in manager._child_devices

    async def test_send_handles_exception(self):
        manager = ConnectionManager()
        device_id = uuid.uuid4()
        child_id = uuid.uuid4()
        ws = AsyncMock()
        ws.send_json.side_effect = RuntimeError("connection closed")

        await manager.connect(device_id, child_id, ws)

        result = await manager.send_to_device(device_id, {"type": "test"})
        assert result is False

    async def test_multiple_children(self):
        manager = ConnectionManager()
        child_a = uuid.uuid4()
        child_b = uuid.uuid4()
        d_a = uuid.uuid4()
        d_b = uuid.uuid4()

        await manager.connect(d_a, child_a, AsyncMock())
        await manager.connect(d_b, child_b, AsyncMock())

        assert await manager.get_connected_count(child_a) == 1
        assert await manager.get_connected_count(child_b) == 1

        count = await manager.send_to_child_devices(child_a, {"type": "test"})
        assert count == 1
