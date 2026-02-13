"""Rule Push Service.

Helper functions to push updated rules to connected devices when parent
makes changes to time rules, TANs, app groups, or device couplings.
"""

import logging
import uuid

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
        rules = await get_current_rules(db, device.id)
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
    rules = await get_current_rules(db, device_id)
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
