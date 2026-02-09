"""Quest Service.

Business logic for quest lifecycle: scheduling instances, validating proofs,
generating TANs on approval, and streak detection.
"""

import uuid
from datetime import datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quest import QuestInstance, QuestTemplate
from app.models.tan import TAN
from app.services.tan_service import generate_tan_code


async def create_instances_for_child(
    db: AsyncSession,
    template: QuestTemplate,
    child_id: uuid.UUID,
) -> QuestInstance:
    """Create a new quest instance from a template for a given child."""
    instance = QuestInstance(
        template_id=template.id,
        child_id=child_id,
        status="available",
    )
    db.add(instance)
    await db.flush()
    await db.refresh(instance)
    return instance


async def claim_quest(
    db: AsyncSession,
    instance: QuestInstance,
) -> QuestInstance:
    """Child claims an available quest."""
    if instance.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quest cannot be claimed (current status: {instance.status})",
        )

    instance.status = "claimed"
    instance.claimed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(instance)
    return instance


async def submit_proof(
    db: AsyncSession,
    instance: QuestInstance,
    proof_type: str,
    proof_url: str,
) -> QuestInstance:
    """Child submits proof for a claimed quest."""
    if instance.status != "claimed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proof can only be submitted for claimed quests (current status: {instance.status})",
        )

    instance.status = "pending_review"
    instance.proof_type = proof_type
    instance.proof_url = proof_url
    await db.flush()
    await db.refresh(instance)
    return instance


async def review_quest(
    db: AsyncSession,
    instance: QuestInstance,
    reviewer_id: uuid.UUID,
    approved: bool,
    feedback: str | None = None,
) -> QuestInstance:
    """Parent reviews a quest submission. On approval, generates a TAN."""
    if instance.status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only quests in pending_review can be reviewed (current status: {instance.status})",
        )

    instance.reviewed_by = reviewer_id
    instance.reviewed_at = datetime.now(timezone.utc)

    if approved:
        instance.status = "approved"

        # Load the template to get reward info
        result = await db.execute(
            select(QuestTemplate).where(QuestTemplate.id == instance.template_id)
        )
        template = result.scalar_one()

        # Generate reward TAN
        tan = await _generate_reward_tan(db, instance, template)
        instance.generated_tan_id = tan.id
    else:
        instance.status = "rejected"

    await db.flush()
    await db.refresh(instance)
    return instance


async def _generate_reward_tan(
    db: AsyncSession,
    instance: QuestInstance,
    template: QuestTemplate,
) -> TAN:
    """Generate a reward TAN when a quest is approved."""
    code = await generate_tan_code(db)
    now = datetime.now(timezone.utc)

    # TAN expires at end of day
    expires_at = datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone.utc)

    tan = TAN(
        child_id=instance.child_id,
        code=code,
        type="time",
        scope_groups=template.tan_groups,
        value_minutes=template.reward_minutes,
        expires_at=expires_at,
        single_use=True,
        source="quest",
        source_quest_id=instance.id,
        status="active",
    )
    db.add(tan)
    await db.flush()
    await db.refresh(tan)
    return tan


async def get_active_streak(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> int:
    """Calculate current streak: consecutive days with at least one approved quest.

    Returns the number of consecutive days (including today if applicable).
    """
    now = datetime.now(timezone.utc)
    today = now.date()

    # Get distinct dates of approved quests, ordered descending
    result = await db.execute(
        select(func.date(QuestInstance.reviewed_at))
        .where(
            QuestInstance.child_id == child_id,
            QuestInstance.status == "approved",
            QuestInstance.reviewed_at.isnot(None),
        )
        .group_by(func.date(QuestInstance.reviewed_at))
        .order_by(func.date(QuestInstance.reviewed_at).desc())
    )
    dates = [row[0] for row in result.all()]

    if not dates:
        return 0

    streak = 0
    expected_date = today

    for d in dates:
        if d == expected_date:
            streak += 1
            expected_date = expected_date.replace(day=expected_date.day - 1) if expected_date.day > 1 else _prev_date(expected_date)
        elif d == _prev_date(expected_date):
            # Allow gap for today if no quest yet
            if streak == 0 and d == _prev_date(today):
                expected_date = d
                streak += 1
                expected_date = _prev_date(expected_date)
            else:
                break
        else:
            break

    return streak


def _prev_date(d) -> "date":
    """Return the previous day."""
    from datetime import timedelta
    return d - timedelta(days=1)


async def get_child_quest_stats(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> dict:
    """Get quest completion stats for a child today."""
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)

    # Quests completed today
    completed_today = await db.execute(
        select(func.count(QuestInstance.id)).where(
            QuestInstance.child_id == child_id,
            QuestInstance.status == "approved",
            QuestInstance.reviewed_at >= today_start,
        )
    )

    # Total available today
    available_today = await db.execute(
        select(func.count(QuestInstance.id)).where(
            QuestInstance.child_id == child_id,
            QuestInstance.created_at >= today_start,
        )
    )

    # Minutes earned today from quest TANs
    earned_result = await db.execute(
        select(func.coalesce(func.sum(TAN.value_minutes), 0)).where(
            TAN.child_id == child_id,
            TAN.source == "quest",
            TAN.created_at >= today_start,
        )
    )

    streak = await get_active_streak(db, child_id)

    return {
        "completed_today": completed_today.scalar() or 0,
        "total_today": available_today.scalar() or 0,
        "minutes_earned_today": earned_result.scalar() or 0,
        "current_streak": streak,
    }
