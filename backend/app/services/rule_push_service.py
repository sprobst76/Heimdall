"""Rule Push Service.

Helper functions to push updated rules to connected devices when parent
makes changes to time rules, TANs, app groups, or device couplings.
Also notifies parent portal WebSockets about dashboard invalidations
and sends real-time notification events (toasts).
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.services.connection_manager import connection_manager
from app.services.rule_engine import get_current_rules

logger = logging.getLogger(__name__)


async def push_rules_to_child_devices(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> int:
    """Push updated rules to all connected devices of a child.

    Returns the count of devices successfully notified.
    """
    result = await db.execute(
        select(Device).where(Device.child_id == child_id)
    )
    devices = result.scalars().all()

    count = 0
    for device in devices:
        rules = await get_current_rules(db, device.id, bypass_cache=True)
        message = {"type": "rules_updated", "rules": rules}
        if await connection_manager.send_to_device(device.id, message):
            count += 1

    logger.info(
        "Pushed rules to %d/%d devices for child %s",
        count, len(devices), child_id,
    )
    return count


async def push_rules_to_device(
    db: AsyncSession,
    device_id: uuid.UUID,
) -> bool:
    """Push updated rules to a specific device.

    Returns True if the device was notified.
    """
    rules = await get_current_rules(db, device_id, bypass_cache=True)
    message = {"type": "rules_updated", "rules": rules}
    return await connection_manager.send_to_device(device_id, message)


async def notify_tan_activated(
    child_id: uuid.UUID,
    tan_id: uuid.UUID,
    tan_type: str,
    value_minutes: int | None = None,
    expires_at: str | None = None,
) -> int:
    """Notify all child devices that a TAN was activated.

    Returns the count of devices successfully notified.
    """
    message = {
        "type": "tan_activated",
        "tan_id": str(tan_id),
        "tan_type": tan_type,
        "value_minutes": value_minutes,
        "expires_at": expires_at,
    }
    return await connection_manager.send_to_child_devices(child_id, message)


async def notify_parent_dashboard(
    family_id: uuid.UUID,
    child_id: uuid.UUID | None = None,
    event_type: str = "update",
) -> int:
    """Notify parent portal to invalidate dashboard data.

    Sends TanStack Query key arrays so the frontend can call
    ``queryClient.invalidateQueries()`` for each key.

    Returns the count of parent connections notified.
    """
    keys: list[list[str]] = [
        ["analytics", "family-dashboard", str(family_id)],
    ]
    if child_id is not None:
        keys.append(["analytics", "child-dashboard", str(child_id)])

    message = {"type": "invalidate", "keys": keys, "event": event_type}
    return await connection_manager.notify_parents(family_id, message)


async def notify_parent_event(
    family_id: uuid.UUID,
    title: str,
    message: str,
    category: str = "info",
    child_id: uuid.UUID | None = None,
) -> int:
    """Send a visible notification event to parent portal WebSockets.

    Categories: info, quest, tan, device.
    Returns the count of parent connections notified.
    """
    payload = {
        "type": "notification",
        "title": title,
        "message": message,
        "category": category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if child_id is not None:
        payload["child_id"] = str(child_id)

    count = await connection_manager.notify_parents(family_id, payload)
    logger.info(
        "Sent notification to %d parents (family %s): %s",
        count, family_id, title,
    )
    return count
