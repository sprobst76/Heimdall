"""TAN Scheduler.

Background service that automatically generates TANs from
scheduled TAN rules (daily, weekdays, weekends, school_days).
"""

import logging
import uuid
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tan import TAN
from app.models.tan_schedule import TanSchedule, TanScheduleLog
from app.models.user import User
from app.services.quest_scheduler import _get_day_info
from app.services.rule_push_service import notify_parent_event
from app.services.tan_service import generate_tan_code

logger = logging.getLogger(__name__)


def _should_generate(schedule: TanSchedule, day_info: dict) -> bool:
    """Check if a schedule should generate a TAN today."""
    recurrence = schedule.recurrence

    if recurrence == "daily":
        return True
    elif recurrence == "weekdays":
        return day_info["is_weekday"]
    elif recurrence == "weekends":
        return not day_info["is_weekday"]
    elif recurrence == "school_days":
        return day_info["is_school_day"]
    return False


async def run_tan_schedules(db: AsyncSession) -> int:
    """Generate TANs for all active schedules matching today.

    Returns the total number of TANs generated.
    """
    today = datetime.now(timezone.utc).date()
    total_generated = 0

    # Load all active schedules with their child's family_id
    result = await db.execute(
        select(TanSchedule, User.family_id).join(
            User, TanSchedule.child_id == User.id,
        ).where(TanSchedule.active == True)  # noqa: E712
    )
    rows = result.all()

    if not rows:
        return 0

    # Group by family for day_info caching
    family_day_info: dict[uuid.UUID, dict] = {}

    for schedule, family_id in rows:
        # Get day info (cached per family)
        if family_id not in family_day_info:
            family_day_info[family_id] = await _get_day_info(db, family_id, today)

        day_info = family_day_info[family_id]

        if not _should_generate(schedule, day_info):
            continue

        # Idempotency: check if already generated today
        existing = await db.execute(
            select(TanScheduleLog).where(
                TanScheduleLog.schedule_id == schedule.id,
                TanScheduleLog.generated_date == today,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        # Generate TAN
        code = await generate_tan_code(db)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=schedule.expires_after_hours)

        tan = TAN(
            child_id=schedule.child_id,
            code=code,
            type=schedule.tan_type,
            scope_groups=schedule.scope_groups,
            scope_devices=schedule.scope_devices,
            value_minutes=schedule.value_minutes,
            value_unlock_until=schedule.value_unlock_until,
            expires_at=expires_at,
            single_use=True,
            source="scheduled",
            status="active",
        )
        db.add(tan)
        await db.flush()
        await db.refresh(tan)

        # Log for idempotency
        log = TanScheduleLog(
            schedule_id=schedule.id,
            generated_date=today,
            generated_tan_id=tan.id,
        )
        db.add(log)

        # Notify parents
        await notify_parent_event(
            family_id,
            "TAN automatisch erstellt",
            f"{schedule.name}: {tan.code}",
            "tan",
            schedule.child_id,
        )

        total_generated += 1

    logger.info("TAN scheduler: %d TANs generated", total_generated)
    return total_generated
