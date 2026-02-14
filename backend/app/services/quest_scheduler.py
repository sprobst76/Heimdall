"""Quest Scheduler.

Background service that automatically creates quest instances from
recurring templates (daily, weekly, school_days) for all children.
"""

import logging
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.day_type import DayTypeOverride
from app.models.family import Family
from app.models.quest import QuestInstance, QuestTemplate
from app.models.user import User
from app.services.quest_service import create_instances_for_child

logger = logging.getLogger(__name__)


async def _get_day_info(
    db: AsyncSession,
    family_id: uuid.UUID,
    today: date,
) -> dict:
    """Determine the day type for a family on a given date.

    Returns dict with is_weekday, is_holiday, is_school_day booleans.
    """
    is_weekday = today.weekday() < 5  # Mon=0 .. Fri=4

    # Check for holiday/vacation overrides
    result = await db.execute(
        select(func.count(DayTypeOverride.id)).where(
            DayTypeOverride.family_id == family_id,
            DayTypeOverride.date == today,
            DayTypeOverride.day_type.in_(["holiday", "vacation"]),
        )
    )
    is_holiday = (result.scalar() or 0) > 0

    return {
        "is_weekday": is_weekday,
        "is_holiday": is_holiday,
        "is_school_day": is_weekday and not is_holiday,
    }


def _should_schedule(
    template: QuestTemplate,
    day_info: dict,
    today: date,
) -> bool:
    """Check if a template should be scheduled today based on recurrence."""
    recurrence = template.recurrence

    if recurrence == "daily":
        return True
    elif recurrence == "weekly":
        # Schedule on the same weekday as template creation
        created_weekday = template.created_at.weekday() if template.created_at else 0
        return today.weekday() == created_weekday
    elif recurrence == "school_days":
        return day_info["is_school_day"]
    else:
        # "once" and unknown types are never auto-scheduled
        return False


async def schedule_daily_quests(
    db: AsyncSession,
    family_id: uuid.UUID | None = None,
) -> int:
    """Create quest instances for all recurring templates.

    If family_id is given, only schedules for that family.
    Otherwise schedules for all families.

    Returns the total number of instances created.
    """
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, time(0, 0), tzinfo=timezone.utc)

    # Load families
    if family_id:
        families_result = await db.execute(
            select(Family).where(Family.id == family_id)
        )
    else:
        families_result = await db.execute(select(Family))
    families = families_result.scalars().all()

    total_created = 0

    for family in families:
        day_info = await _get_day_info(db, family.id, today)

        # Load active recurring templates for this family
        templates_result = await db.execute(
            select(QuestTemplate).where(
                QuestTemplate.family_id == family.id,
                QuestTemplate.active == True,  # noqa: E712
                QuestTemplate.recurrence.in_(["daily", "weekly", "school_days"]),
            )
        )
        templates = templates_result.scalars().all()

        if not templates:
            continue

        # Load children in this family
        children_result = await db.execute(
            select(User).where(
                User.family_id == family.id,
                User.role == "child",
            )
        )
        children = children_result.scalars().all()

        if not children:
            continue

        for template in templates:
            if not _should_schedule(template, day_info, today):
                continue

            for child in children:
                # Check if instance already exists today
                existing = await db.execute(
                    select(func.count(QuestInstance.id)).where(
                        QuestInstance.template_id == template.id,
                        QuestInstance.child_id == child.id,
                        QuestInstance.created_at >= today_start,
                    )
                )
                if (existing.scalar() or 0) > 0:
                    continue

                await create_instances_for_child(db, template, child.id)
                total_created += 1

    logger.info(
        "Quest scheduler: created %d instances for %d families",
        total_created, len(families),
    )
    return total_created
