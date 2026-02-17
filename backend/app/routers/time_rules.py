"""Time Rules router.

Endpoints for managing screen-time rules for a child.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.time_rule import TimeRule
from app.models.user import User
from app.schemas.time_rule import TimeRuleCreate, TimeRuleResponse, TimeRuleUpdate
from app.services.rule_push_service import push_rules_to_child_devices

router = APIRouter(prefix="/children/{child_id}/rules", tags=["Time Rules"])


async def _verify_child_access(
    db: AsyncSession, child_id: uuid.UUID, current_user: User
) -> User:
    """Verify the current user has access to this child's data."""
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    if child.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    return child


@router.get("/", response_model=list[TimeRuleResponse])
async def list_rules(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """List all time rules for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TimeRule)
        .where(TimeRule.child_id == child_id)
        .order_by(TimeRule.priority.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=TimeRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    child_id: uuid.UUID,
    body: TimeRuleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Create a new time rule for a child. Requires parent role."""
    await _verify_child_access(db, child_id, current_user)

    rule = TimeRule(
        child_id=child_id,
        name=body.name,
        target_type=body.target_type,
        target_id=body.target_id,
        day_types=body.day_types,
        time_windows=[tw.model_dump() for tw in body.time_windows],
        daily_limit_minutes=body.daily_limit_minutes,
        group_limits=[gl.model_dump(mode="json") for gl in body.group_limits],
        priority=body.priority,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    await push_rules_to_child_devices(db, child_id)
    return rule


@router.get("/{rule_id}", response_model=TimeRuleResponse)
async def get_rule(
    child_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Get a specific time rule."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TimeRule).where(
            TimeRule.id == rule_id,
            TimeRule.child_id == child_id,
        )
    )
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time rule not found",
        )

    return rule


@router.put("/{rule_id}", response_model=TimeRuleResponse)
async def update_rule(
    child_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: TimeRuleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Update a time rule. Requires parent role."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TimeRule).where(
            TimeRule.id == rule_id,
            TimeRule.child_id == child_id,
        )
    )
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time rule not found",
        )

    update_data = body.model_dump(exclude_unset=True)

    # Serialize Pydantic sub-models to dicts for JSON columns
    if "time_windows" in update_data and update_data["time_windows"] is not None:
        update_data["time_windows"] = [
            tw.model_dump() if hasattr(tw, "model_dump") else tw
            for tw in update_data["time_windows"]
        ]
    if "group_limits" in update_data and update_data["group_limits"] is not None:
        update_data["group_limits"] = [
            gl.model_dump(mode="json") if hasattr(gl, "model_dump") else gl
            for gl in update_data["group_limits"]
        ]

    _allowed = {"name", "day_types", "time_windows", "daily_limit_minutes", "group_limits", "priority", "active", "valid_from", "valid_until"}
    for field, value in update_data.items():
        if field in _allowed:
            setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    await push_rules_to_child_devices(db, child_id)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    child_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Delete a time rule. Requires parent role."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TimeRule).where(
            TimeRule.id == rule_id,
            TimeRule.child_id == child_id,
        )
    )
    rule = result.scalar_one_or_none()

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time rule not found",
        )

    await db.delete(rule)
    await db.flush()
    await push_rules_to_child_devices(db, child_id)
    return None
