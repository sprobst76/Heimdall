"""WebSocket Connection Manager.

Manages active device WebSocket connections for real-time push notifications.
"""

import asyncio
import logging
import uuid

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Singleton manager for active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, WebSocket] = {}
        self._child_devices: dict[uuid.UUID, set[uuid.UUID]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self, device_id: uuid.UUID, child_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        """Register a new device connection."""
        async with self._lock:
            self._connections[device_id] = websocket
            if child_id not in self._child_devices:
                self._child_devices[child_id] = set()
            self._child_devices[child_id].add(device_id)
        logger.info("Device %s connected (child %s)", device_id, child_id)

    async def disconnect(
        self, device_id: uuid.UUID, child_id: uuid.UUID
    ) -> None:
        """Remove a device connection."""
        async with self._lock:
            self._connections.pop(device_id, None)
            if child_id in self._child_devices:
                self._child_devices[child_id].discard(device_id)
                if not self._child_devices[child_id]:
                    del self._child_devices[child_id]
        logger.info("Device %s disconnected (child %s)", device_id, child_id)

    async def send_to_device(
        self, device_id: uuid.UUID, message: dict
    ) -> bool:
        """Send a message to a specific device.

        Returns True if sent successfully, False if not connected.
        """
        websocket = self._connections.get(device_id)
        if websocket is None:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception:
            logger.warning("Failed to send to device %s", device_id)
            return False

    async def send_to_child_devices(
        self, child_id: uuid.UUID, message: dict
    ) -> int:
        """Send a message to all connected devices of a child.

        Returns the count of devices successfully notified.
        """
        device_ids = self._child_devices.get(child_id, set()).copy()
        count = 0
        for device_id in device_ids:
            if await self.send_to_device(device_id, message):
                count += 1
        return count

    async def is_connected(self, device_id: uuid.UUID) -> bool:
        """Check if a device is currently connected."""
        return device_id in self._connections

    async def get_connected_count(self, child_id: uuid.UUID) -> int:
        """Get count of connected devices for a child."""
        return len(self._child_devices.get(child_id, set()))


# Singleton instance
connection_manager = ConnectionManager()
