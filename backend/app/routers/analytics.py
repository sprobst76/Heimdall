from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_parent
from app.database import get_db
from app.schemas.analytics import (
    AnalyticsResponse,
    ChildDashboardStats,
    FamilyDashboardStats,
)
from app.services.analytics_service import (
    get_child_analytics,
    get_child_dashboard_stats,
    get_family_dashboard_stats,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/family/{family_id}/dashboard",
    response_model=FamilyDashboardStats,
)
async def family_dashboard(
    family_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _parent: dict = Depends(require_parent),
) -> FamilyDashboardStats:
    """Return aggregate stats for the family dashboard header cards."""
    data = await get_family_dashboard_stats(db, family_id)
    return FamilyDashboardStats(**data)


@router.get(
    "/children/{child_id}/dashboard",
    response_model=ChildDashboardStats,
)
async def child_dashboard(
    child_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _parent: dict = Depends(require_parent),
) -> ChildDashboardStats:
    """Return real-time stats for one child on the parent dashboard."""
    data = await get_child_dashboard_stats(db, child_id)
    return ChildDashboardStats(**data)


@router.get(
    "/children/{child_id}/report",
    response_model=AnalyticsResponse,
)
async def child_report(
    child_id: uuid.UUID,
    period: str = Query("week", pattern="^(day|week|month)$"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _parent: dict = Depends(require_parent),
) -> AnalyticsResponse:
    """Return detailed analytics / report for a child over a date range.

    If *start_date* and *end_date* are omitted they are derived from
    *period*:
    - ``day``  : today
    - ``week`` : last 7 days
    - ``month``: last 30 days
    """
    today = date.today()

    if start_date is None or end_date is None:
        if period == "day":
            start_date = today
            end_date = today
        elif period == "week":
            start_date = today - timedelta(days=6)
            end_date = today
        else:  # month
            start_date = today - timedelta(days=29)
            end_date = today

    data = await get_child_analytics(db, child_id, period, start_date, end_date)
    return AnalyticsResponse(**data)
