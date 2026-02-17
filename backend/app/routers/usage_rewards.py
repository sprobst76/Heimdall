"""Usage Reward Rules — CRUD + History."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.usage_reward import UsageRewardLog, UsageRewardRule
from app.models.user import User
from app.schemas.usage_reward import (
    UsageRewardLogResponse,
    UsageRewardRuleCreate,
    UsageRewardRuleResponse,
    UsageRewardRuleUpdate,
)

router = APIRouter(tags=["Usage Rewards"])

VALID_TRIGGER_TYPES = {"daily_under", "streak_under", "group_free"}


async def _verify_child_access(
    db: AsyncSession,
    child_id: uuid.UUID,
    current_user: User,
) -> User:
    """Verify the current user has parent access to this child."""
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Kind nicht gefunden",
        )
    if child.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf dieses Kind",
        )
    return child


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_id}/usage-rewards/",
    response_model=list[UsageRewardRuleResponse],
)
async def list_usage_reward_rules(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> list[UsageRewardRule]:
    """List all usage reward rules for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(UsageRewardRule)
        .where(
            and_(
                UsageRewardRule.child_id == child_id,
                UsageRewardRule.active.is_(True),
            ),
        )
        .order_by(UsageRewardRule.created_at),
    )
    return list(result.scalars().all())


@router.post(
    "/children/{child_id}/usage-rewards/",
    response_model=UsageRewardRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_usage_reward_rule(
    child_id: uuid.UUID,
    body: UsageRewardRuleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> UsageRewardRule:
    """Create a new usage reward rule."""
    await _verify_child_access(db, child_id, current_user)

    if body.trigger_type not in VALID_TRIGGER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Trigger-Typ. Erlaubt: {', '.join(VALID_TRIGGER_TYPES)}",
        )
    if body.trigger_type == "streak_under" and (body.streak_days is None or body.streak_days < 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="streak_days muss mindestens 2 sein",
        )
    if body.threshold_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold_minutes muss größer als 0 sein",
        )
    if body.reward_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reward_minutes muss größer als 0 sein",
        )

    rule = UsageRewardRule(
        child_id=child_id,
        name=body.name,
        trigger_type=body.trigger_type,
        threshold_minutes=body.threshold_minutes,
        target_group_id=body.target_group_id,
        streak_days=body.streak_days,
        reward_minutes=body.reward_minutes,
        reward_group_ids=body.reward_group_ids,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put(
    "/children/{child_id}/usage-rewards/{rule_id}",
    response_model=UsageRewardRuleResponse,
)
async def update_usage_reward_rule(
    child_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: UsageRewardRuleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> UsageRewardRule:
    """Update an existing usage reward rule."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(UsageRewardRule).where(
            and_(UsageRewardRule.id == rule_id, UsageRewardRule.child_id == child_id),
        ),
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Regel nicht gefunden",
        )

    update_data = body.model_dump(exclude_unset=True)
    if "trigger_type" in update_data and update_data["trigger_type"] not in VALID_TRIGGER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Trigger-Typ. Erlaubt: {', '.join(VALID_TRIGGER_TYPES)}",
        )

    _allowed = {"name", "trigger_type", "threshold_minutes", "target_group_id", "streak_days", "reward_minutes", "reward_group_ids", "active"}
    for key, value in update_data.items():
        if key in _allowed:
            setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete(
    "/children/{child_id}/usage-rewards/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_usage_reward_rule(
    child_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> None:
    """Soft-delete a usage reward rule (set active=False)."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(UsageRewardRule).where(
            and_(UsageRewardRule.id == rule_id, UsageRewardRule.child_id == child_id),
        ),
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Regel nicht gefunden",
        )

    rule.active = False
    await db.commit()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_id}/usage-rewards/history",
    response_model=list[UsageRewardLogResponse],
)
async def get_usage_reward_history(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> list[UsageRewardLog]:
    """Get the last 30 reward evaluations for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(UsageRewardLog)
        .where(UsageRewardLog.child_id == child_id)
        .order_by(UsageRewardLog.evaluated_date.desc())
        .limit(30),
    )
    return list(result.scalars().all())
