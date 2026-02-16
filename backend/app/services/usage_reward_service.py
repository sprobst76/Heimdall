"""Usage Reward Service.

Evaluates usage reward rules and generates bonus TANs for children
who stay under their screen time limits.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tan import TAN
from app.models.usage import UsageEvent
from app.models.usage_reward import UsageRewardLog, UsageRewardRule
from app.services.tan_service import generate_tan_code

logger = logging.getLogger(__name__)


async def evaluate_daily_rewards(db: AsyncSession) -> int:
    """Evaluate all active rules for yesterday's usage.

    Returns the number of TANs generated.
    """
    yesterday = date.today() - timedelta(days=1)

    result = await db.execute(
        select(UsageRewardRule).where(UsageRewardRule.active.is_(True)),
    )
    rules = result.scalars().all()

    count = 0
    for rule in rules:
        # Idempotency: skip if already evaluated for this date
        existing = await db.execute(
            select(UsageRewardLog).where(
                and_(
                    UsageRewardLog.rule_id == rule.id,
                    UsageRewardLog.evaluated_date == yesterday,
                ),
            ),
        )
        if existing.scalar_one_or_none() is not None:
            continue

        usage_minutes = await _get_usage_minutes(db, rule, yesterday)
        rewarded = await _check_trigger(db, rule, usage_minutes, yesterday)

        tan = None
        if rewarded:
            tan = await _generate_reward_tan(db, rule)
            count += 1

        log = UsageRewardLog(
            rule_id=rule.id,
            child_id=rule.child_id,
            evaluated_date=yesterday,
            usage_minutes=usage_minutes,
            threshold_minutes=rule.threshold_minutes,
            rewarded=rewarded,
            generated_tan_id=tan.id if tan else None,
        )
        db.add(log)

        if rewarded:
            logger.info(
                "Usage reward: %s for child %s — %d min (limit %d) → +%d min TAN",
                rule.name, rule.child_id, usage_minutes,
                rule.threshold_minutes, rule.reward_minutes,
            )

    return count


async def _get_usage_minutes(
    db: AsyncSession,
    rule: UsageRewardRule,
    target_date: date,
) -> int:
    """Sum usage minutes for a child on a given date, optionally filtered by group."""
    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    conditions = [
        UsageEvent.child_id == rule.child_id,
        UsageEvent.started_at >= day_start,
        UsageEvent.started_at < day_end,
    ]

    if rule.target_group_id is not None:
        conditions.append(UsageEvent.app_group_id == rule.target_group_id)

    result = await db.execute(
        select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0)).where(
            and_(*conditions),
        ),
    )
    total_seconds: int = result.scalar_one()
    return total_seconds // 60


async def _check_trigger(
    db: AsyncSession,
    rule: UsageRewardRule,
    usage_minutes: int,
    target_date: date,
) -> bool:
    """Check if the rule's trigger condition is met."""
    if rule.trigger_type == "daily_under":
        return usage_minutes < rule.threshold_minutes

    if rule.trigger_type == "group_free":
        return usage_minutes == 0

    if rule.trigger_type == "streak_under":
        return await _check_streak(db, rule, usage_minutes, target_date)

    return False


async def _check_streak(
    db: AsyncSession,
    rule: UsageRewardRule,
    today_usage: int,
    target_date: date,
) -> bool:
    """Check if child has N consecutive days under the limit (including target_date)."""
    streak_days = rule.streak_days or 3

    # Today must also be under limit
    if today_usage >= rule.threshold_minutes:
        return False

    # Check the previous (streak_days - 1) days in the log
    needed = streak_days - 1
    if needed == 0:
        return True

    result = await db.execute(
        select(UsageRewardLog)
        .where(
            and_(
                UsageRewardLog.rule_id == rule.id,
                UsageRewardLog.evaluated_date >= target_date - timedelta(days=needed),
                UsageRewardLog.evaluated_date < target_date,
            ),
        )
        .order_by(UsageRewardLog.evaluated_date.desc()),
    )
    logs = result.scalars().all()

    if len(logs) < needed:
        return False

    # All previous days must have been under limit (usage < threshold)
    return all(log.usage_minutes < rule.threshold_minutes for log in logs)


async def _generate_reward_tan(
    db: AsyncSession,
    rule: UsageRewardRule,
) -> TAN:
    """Generate a bonus TAN for the child."""
    code = await generate_tan_code(db)
    now = datetime.now(timezone.utc)

    # TAN expires at end of day
    expires_at = datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone.utc)

    tan = TAN(
        child_id=rule.child_id,
        code=code,
        type="time",
        scope_groups=rule.reward_group_ids,
        value_minutes=rule.reward_minutes,
        expires_at=expires_at,
        single_use=True,
        source="usage_reward",
        status="active",
    )
    db.add(tan)
    await db.flush()
    await db.refresh(tan)
    return tan
