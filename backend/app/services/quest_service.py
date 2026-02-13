"""Quest Service.

Business logic for quest lifecycle: scheduling instances, validating proofs,
generating TANs on approval, and streak detection.
"""

import uuid
from datetime import datetime, time, timezone

import logging

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quest import QuestInstance, QuestTemplate
from app.models.tan import TAN
from app.models.usage import UsageEvent
from app.models.user import User
from app.services.tan_service import generate_tan_code

logger = logging.getLogger(__name__)


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
    """Child submits proof for a claimed quest.

    If the quest template has ai_verify enabled and an API key is configured,
    the proof is automatically verified. High-confidence results (>=80%) trigger
    auto-approval with TAN generation.
    """
    if instance.status != "claimed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proof can only be submitted for claimed quests (current status: {instance.status})",
        )

    instance.status = "pending_review"
    instance.proof_type = proof_type
    instance.proof_url = proof_url
    await db.flush()

    # Attempt AI verification if enabled
    from app.config import settings

    if settings.ANTHROPIC_API_KEY:
        result = await db.execute(
            select(QuestTemplate).where(QuestTemplate.id == instance.template_id)
        )
        template = result.scalar_one()

        if template.ai_verify:
            from app.services.llm_service import verify_quest_proof

            ai_result = await verify_quest_proof(
                image_path=proof_url,
                quest_name=template.name,
                quest_description=template.description,
                ai_prompt=template.ai_prompt,
            )
            instance.ai_result = ai_result
            await db.flush()

            # Auto-approve if high confidence
            threshold = settings.LLM_AUTO_APPROVE_THRESHOLD
            if ai_result.get("approved") and ai_result.get("confidence", 0) >= threshold:
                instance = await review_quest(
                    db, instance, instance.child_id,
                    approved=True, feedback=ai_result.get("feedback"),
                )

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

    # Check if streak bonus triggered after approval
    if approved:
        await check_streak_bonus(db, instance.child_id)

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
    # func.date() returns strings on SQLite, date objects on PostgreSQL
    raw_dates = [row[0] for row in result.all()]
    from datetime import date as date_type
    dates = []
    for d in raw_dates:
        if isinstance(d, str):
            dates.append(date_type.fromisoformat(d))
        elif isinstance(d, date_type):
            dates.append(d)
        elif d is not None:
            dates.append(d)

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


async def check_auto_detect_quests(
    db: AsyncSession,
    child_id: uuid.UUID,
    app_package: str,
) -> list[QuestInstance]:
    """Check if any auto-detect quests are satisfied by current usage.

    Called after usage events. If today's total usage for app_package
    meets a quest's auto_detect_minutes threshold, the quest is
    automatically claimed and approved with a reward TAN.

    Returns list of auto-approved instances.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)

    # Find child's family
    child_result = await db.execute(select(User).where(User.id == child_id))
    child = child_result.scalar_one_or_none()
    if child is None:
        return []

    # Find matching auto-detect templates
    templates_result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.family_id == child.family_id,
            QuestTemplate.active == True,  # noqa: E712
            QuestTemplate.auto_detect_app == app_package,
            QuestTemplate.auto_detect_minutes.isnot(None),
        )
    )
    templates = templates_result.scalars().all()

    if not templates:
        return []

    # Calculate today's total usage for this app
    usage_result = await db.execute(
        select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0)).where(
            UsageEvent.child_id == child_id,
            UsageEvent.app_package == app_package,
            UsageEvent.started_at >= today_start,
        )
    )
    total_seconds = usage_result.scalar() or 0

    approved_instances = []

    for template in templates:
        threshold_seconds = template.auto_detect_minutes * 60
        if total_seconds < threshold_seconds:
            continue

        # Find open instance for this template (available or claimed)
        instance_result = await db.execute(
            select(QuestInstance).where(
                QuestInstance.template_id == template.id,
                QuestInstance.child_id == child_id,
                QuestInstance.status.in_(["available", "claimed"]),
                QuestInstance.created_at >= today_start,
            )
        )
        instance = instance_result.scalar_one_or_none()

        if instance is None:
            continue

        # Auto-approve: claim → approve → generate TAN
        if instance.status == "available":
            instance.status = "claimed"
            instance.claimed_at = now

        instance.status = "approved"
        instance.proof_type = "auto"
        instance.reviewed_at = now

        tan = await _generate_reward_tan(db, instance, template)
        instance.generated_tan_id = tan.id

        await db.flush()
        await db.refresh(instance)
        approved_instances.append(instance)

        logger.info(
            "Auto-detect quest approved: child=%s, app=%s, template=%s",
            child_id, app_package, template.name,
        )

    # Check streak bonus if any quests were auto-approved
    if approved_instances:
        await check_streak_bonus(db, child_id)

    return approved_instances


async def check_streak_bonus(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> QuestInstance | None:
    """Check if child qualifies for a streak bonus quest.

    Called after quest approval. If the child's current streak meets
    a streak template's threshold and no bonus was awarded today,
    auto-creates and approves the bonus quest with a reward TAN.

    Returns the bonus instance or None.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)

    streak = await get_active_streak(db, child_id)
    if streak < 1:
        return None

    # Find child's family
    child_result = await db.execute(select(User).where(User.id == child_id))
    child = child_result.scalar_one_or_none()
    if child is None:
        return None

    # Find streak bonus templates that match current streak
    templates_result = await db.execute(
        select(QuestTemplate).where(
            QuestTemplate.family_id == child.family_id,
            QuestTemplate.active == True,  # noqa: E712
            QuestTemplate.streak_threshold.isnot(None),
            QuestTemplate.streak_threshold <= streak,
        )
    )
    templates = templates_result.scalars().all()

    for template in templates:
        # Check if bonus already awarded today for this template
        existing_result = await db.execute(
            select(func.count(QuestInstance.id)).where(
                QuestInstance.template_id == template.id,
                QuestInstance.child_id == child_id,
                QuestInstance.status == "approved",
                QuestInstance.reviewed_at >= today_start,
            )
        )
        already_awarded = (existing_result.scalar() or 0) > 0

        if already_awarded:
            continue

        # Create and auto-approve streak bonus
        instance = QuestInstance(
            template_id=template.id,
            child_id=child_id,
            status="approved",
            claimed_at=now,
            proof_type="auto",
            reviewed_at=now,
        )
        db.add(instance)
        await db.flush()

        tan = await _generate_reward_tan(db, instance, template)
        instance.generated_tan_id = tan.id

        await db.flush()
        await db.refresh(instance)

        logger.info(
            "Streak bonus awarded: child=%s, streak=%d, template=%s, reward=%d min",
            child_id, streak, template.name, template.reward_minutes,
        )
        return instance

    return None
