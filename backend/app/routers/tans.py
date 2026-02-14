"""TANs router.

Endpoints for generating, listing, redeeming, and invalidating TANs.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.tan import TAN
from app.models.user import User
from app.schemas.tan import TANCreate, TANRedeemRequest, TANResponse
from app.services.rule_push_service import notify_parent_dashboard, notify_tan_activated, push_rules_to_child_devices
from app.services.tan_service import generate_tan_code, redeem_tan, validate_tan_redemption

router = APIRouter(prefix="/children/{child_id}/tans", tags=["TANs"])


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


@router.get("/", response_model=list[TANResponse])
async def list_tans(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
    tan_status: str | None = Query(None, alias="status", description="Filter by TAN status"),
):
    """List TANs for a child, optionally filtered by status."""
    await _verify_child_access(db, child_id, current_user)

    query = select(TAN).where(TAN.child_id == child_id)

    if tan_status is not None:
        query = query.where(TAN.status == tan_status)

    query = query.order_by(TAN.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/generate", response_model=TANResponse, status_code=status.HTTP_201_CREATED)
async def generate_tan(
    child_id: uuid.UUID,
    body: TANCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Generate a new TAN for a child. Requires parent role."""
    await _verify_child_access(db, child_id, current_user)

    # Generate a unique code
    code = await generate_tan_code(db)

    # Compute default expiry if not provided (end of current day)
    from datetime import datetime, time, timezone

    expires_at = body.expires_at
    if expires_at is None:
        now = datetime.now(timezone.utc)
        expires_at = datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone.utc)

    # Parse value_unlock_until if provided
    value_unlock_until = None
    if body.value_unlock_until is not None:
        parts = body.value_unlock_until.split(":")
        from datetime import time as time_type

        value_unlock_until = time_type(int(parts[0]), int(parts[1]))

    tan = TAN(
        child_id=child_id,
        code=code,
        type=body.type,
        scope_groups=body.scope_groups,
        scope_devices=body.scope_devices,
        value_minutes=body.value_minutes,
        value_unlock_until=value_unlock_until,
        expires_at=expires_at,
        single_use=body.single_use,
        source="parent_manual",
        status="active",
    )
    db.add(tan)
    await db.flush()
    await db.refresh(tan)
    return tan


@router.post("/redeem", response_model=TANResponse)
async def redeem_tan_endpoint(
    child_id: uuid.UUID,
    body: TANRedeemRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Redeem a TAN by code. Validates all policies."""
    child_obj = await _verify_child_access(db, child_id, current_user)

    # Look up the TAN by code
    result = await db.execute(
        select(TAN).where(TAN.code == body.code, TAN.child_id == child_id)
    )
    tan = result.scalar_one_or_none()

    if tan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TAN not found",
        )

    # Validate all redemption policies
    await validate_tan_redemption(db, tan, child_id)

    # Redeem the TAN
    await redeem_tan(db, tan)

    # Notify devices about TAN activation + push updated rules
    await notify_tan_activated(
        child_id=child_id,
        tan_id=tan.id,
        tan_type=tan.type,
        value_minutes=tan.value_minutes,
        expires_at=tan.expires_at.isoformat() if tan.expires_at else None,
    )
    await push_rules_to_child_devices(db, child_id)

    # Notify parent dashboard
    await notify_parent_dashboard(child_obj.family_id, child_id, "tan_redeemed")

    return tan


@router.delete("/{tan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_tan(
    child_id: uuid.UUID,
    tan_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Invalidate (expire) a TAN. Requires parent role."""
    child_obj = await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TAN).where(
            TAN.id == tan_id,
            TAN.child_id == child_id,
        )
    )
    tan = result.scalar_one_or_none()

    if tan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TAN not found",
        )

    tan.status = "expired"
    await db.flush()
    await push_rules_to_child_devices(db, child_id)
    await notify_parent_dashboard(child_obj.family_id, child_id, "tan_invalidated")
    return None
