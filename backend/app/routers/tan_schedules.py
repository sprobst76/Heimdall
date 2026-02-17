"""TAN Schedules — CRUD + Log History."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_parent
from app.database import get_db
from app.models.tan_schedule import TanSchedule, TanScheduleLog
from app.models.user import User
from app.schemas.tan_schedule import (
    TanScheduleCreate,
    TanScheduleLogResponse,
    TanScheduleResponse,
    TanScheduleUpdate,
)

router = APIRouter(tags=["TAN Schedules"])

VALID_RECURRENCES = {"daily", "weekdays", "weekends", "school_days"}
VALID_TAN_TYPES = {"time", "group_unlock", "extend_window", "override"}


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
    "/children/{child_id}/tan-schedules/",
    response_model=list[TanScheduleResponse],
)
async def list_tan_schedules(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> list[TanSchedule]:
    """List all TAN schedules for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TanSchedule)
        .where(TanSchedule.child_id == child_id)
        .order_by(TanSchedule.created_at),
    )
    return list(result.scalars().all())


@router.post(
    "/children/{child_id}/tan-schedules/",
    response_model=TanScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tan_schedule(
    child_id: uuid.UUID,
    body: TanScheduleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> TanSchedule:
    """Create a new TAN schedule."""
    await _verify_child_access(db, child_id, current_user)

    if body.recurrence not in VALID_RECURRENCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültige Wiederholung. Erlaubt: {', '.join(VALID_RECURRENCES)}",
        )
    if body.tan_type not in VALID_TAN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger TAN-Typ. Erlaubt: {', '.join(VALID_TAN_TYPES)}",
        )
    if body.tan_type == "time" and (body.value_minutes is None or body.value_minutes <= 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="value_minutes muss für Typ 'time' angegeben werden und > 0 sein",
        )

    schedule = TanSchedule(
        child_id=child_id,
        name=body.name,
        recurrence=body.recurrence,
        tan_type=body.tan_type,
        value_minutes=body.value_minutes,
        scope_groups=body.scope_groups,
        scope_devices=body.scope_devices,
        expires_after_hours=body.expires_after_hours,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.put(
    "/children/{child_id}/tan-schedules/{schedule_id}",
    response_model=TanScheduleResponse,
)
async def update_tan_schedule(
    child_id: uuid.UUID,
    schedule_id: uuid.UUID,
    body: TanScheduleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> TanSchedule:
    """Update an existing TAN schedule."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TanSchedule).where(
            and_(TanSchedule.id == schedule_id, TanSchedule.child_id == child_id),
        ),
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="TAN-Regel nicht gefunden",
        )

    update_data = body.model_dump(exclude_unset=True)
    if "recurrence" in update_data and update_data["recurrence"] not in VALID_RECURRENCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültige Wiederholung. Erlaubt: {', '.join(VALID_RECURRENCES)}",
        )
    if "tan_type" in update_data and update_data["tan_type"] not in VALID_TAN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger TAN-Typ. Erlaubt: {', '.join(VALID_TAN_TYPES)}",
        )

    _allowed = {"name", "recurrence", "tan_type", "value_minutes", "value_unlock_until", "scope_groups", "scope_devices", "expires_after_hours", "active"}
    for key, value in update_data.items():
        if key in _allowed:
            setattr(schedule, key, value)

    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete(
    "/children/{child_id}/tan-schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tan_schedule(
    child_id: uuid.UUID,
    schedule_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> None:
    """Delete a TAN schedule."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TanSchedule).where(
            and_(TanSchedule.id == schedule_id, TanSchedule.child_id == child_id),
        ),
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="TAN-Regel nicht gefunden",
        )

    await db.delete(schedule)
    await db.commit()


# ---------------------------------------------------------------------------
# Log History
# ---------------------------------------------------------------------------


@router.get(
    "/children/{child_id}/tan-schedules/{schedule_id}/logs",
    response_model=list[TanScheduleLogResponse],
)
async def get_tan_schedule_logs(
    child_id: uuid.UUID,
    schedule_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> list[TanScheduleLog]:
    """Get the last 30 TAN generation logs for a schedule."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(TanScheduleLog)
        .where(TanScheduleLog.schedule_id == schedule_id)
        .order_by(TanScheduleLog.generated_date.desc())
        .limit(30),
    )
    return list(result.scalars().all())
