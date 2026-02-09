from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel


class GroupUsage(BaseModel):
    """Usage breakdown for a single app group."""

    app_group_id: uuid.UUID | None
    group_name: str
    minutes: int
    percentage: float  # 0-100


class DailySummary(BaseModel):
    """Single day summary for one child."""

    date: date
    total_minutes: int
    group_breakdown: list[GroupUsage]
    quests_completed: int
    tans_redeemed: int
    blocked_attempts: int


class HeatmapEntry(BaseModel):
    """Usage intensity for one hour-of-day / day-of-week cell."""

    hour: int  # 0-23
    day: int  # 0=Mon, 6=Sun
    minutes: float


class WeeklyTrend(BaseModel):
    """Aggregated totals for a single ISO week."""

    week_start: date
    total_minutes: int
    quests_completed: int
    tans_redeemed: int


class ChildDashboardStats(BaseModel):
    """Real-time stats for one child on the dashboard."""

    child_id: uuid.UUID
    child_name: str
    usage_today_minutes: int
    daily_limit_minutes: int | None
    active_tans: int
    quests_completed_today: int
    current_streak: int
    devices_online: int
    top_group: str | None  # most-used group today


class FamilyDashboardStats(BaseModel):
    """Aggregate stats for the family dashboard header."""

    total_children: int
    total_active_rules: int
    tans_today: int
    total_usage_today_minutes: int


class AnalyticsResponse(BaseModel):
    """Full analytics response for a child."""

    child_id: uuid.UUID
    child_name: str
    period: str  # "day" | "week" | "month"
    daily_summaries: list[DailySummary]
    heatmap: list[HeatmapEntry]
    trends: list[WeeklyTrend]
    group_breakdown: list[GroupUsage]
