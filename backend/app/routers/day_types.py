"""Day Types router.

Endpoints for managing day type overrides (holidays, vacation days, etc.)
for a family.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_family_member, require_parent
from app.database import get_db
from app.models.day_type import DayTypeOverride
from app.models.user import User
from app.schemas.day_type import (
    DayTypeOverrideCreate,
    DayTypeOverrideResponse,
    HolidaySyncRequest,
)
from app.services.holiday_service import sync_holidays_to_db

router = APIRouter(prefix="/families/{family_id}/day-types", tags=["Day Types"])


@router.get("/", response_model=list[DayTypeOverrideResponse])
async def list_day_type_overrides(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
    date_from: date | None = Query(None, description="Filter from date (inclusive)"),
    date_to: date | None = Query(None, description="Filter to date (inclusive)"),
):
    """List day type overrides for a family with optional date range filter."""
    query = select(DayTypeOverride).where(
        DayTypeOverride.family_id == family_id
    )

    if date_from is not None:
        query = query.where(DayTypeOverride.date >= date_from)
    if date_to is not None:
        query = query.where(DayTypeOverride.date <= date_to)

    query = query.order_by(DayTypeOverride.date)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=DayTypeOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_day_type_override(
    family_id: uuid.UUID,
    body: DayTypeOverrideCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Create a manual day type override. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    # Check for existing override on this date
    existing = await db.execute(
        select(DayTypeOverride).where(
            DayTypeOverride.family_id == family_id,
            DayTypeOverride.date == body.date,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An override already exists for this date",
        )

    override = DayTypeOverride(
        family_id=family_id,
        date=body.date,
        day_type=body.day_type,
        label=body.label,
        source="manual",
    )
    db.add(override)
    await db.flush()
    await db.refresh(override)
    return override


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_day_type_override(
    family_id: uuid.UUID,
    override_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Remove a day type override. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(DayTypeOverride).where(
            DayTypeOverride.id == override_id,
            DayTypeOverride.family_id == family_id,
        )
    )
    override = result.scalar_one_or_none()

    if override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found",
        )

    await db.delete(override)
    await db.flush()
    return None


@router.post("/sync-holidays", response_model=list[DayTypeOverrideResponse])
async def sync_holidays(
    family_id: uuid.UUID,
    body: HolidaySyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Fetch holidays from OpenHolidays API and store as overrides."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    created = await sync_holidays_to_db(
        db=db,
        family_id=family_id,
        year=body.year,
        subdivision=body.subdivision,
    )
    return created
