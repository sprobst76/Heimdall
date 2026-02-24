from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select, func, and_, extract, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_group import AppGroup
from app.models.device import Device
from app.models.quest import QuestInstance, QuestTemplate
from app.models.tan import TAN
from app.models.time_rule import TimeRule
from app.models.usage import UsageEvent
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _day_bounds(d: date) -> tuple[datetime, datetime]:
    """Return (start-of-day UTC, start-of-next-day UTC) for a given date."""
    start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _period_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end datetimes for a date range."""
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


# ---------------------------------------------------------------------------
# Family dashboard
# ---------------------------------------------------------------------------

async def get_family_dashboard_stats(
    db: AsyncSession,
    family_id: uuid.UUID,
) -> dict:
    """Get aggregate stats for family dashboard header cards.

    Single DB roundtrip using scalar subqueries.
    """

    today_start, today_end = _day_bounds(date.today())

    # Child-IDs as reusable subquery
    children_subq = select(User.id).where(
        User.family_id == family_id, User.role == "child"
    )

    row = (await db.execute(select(
        select(func.count(User.id)).where(
            User.family_id == family_id, User.role == "child"
        ).scalar_subquery().label("total_children"),
        select(func.count()).select_from(TimeRule).where(
            TimeRule.child_id.in_(children_subq),
            TimeRule.active.is_(True),
        ).scalar_subquery().label("total_active_rules"),
        select(func.count()).select_from(TAN).where(
            TAN.child_id.in_(children_subq),
            TAN.created_at >= today_start,
            TAN.created_at < today_end,
        ).scalar_subquery().label("tans_today"),
        select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0)).where(
            UsageEvent.child_id.in_(children_subq),
            UsageEvent.started_at >= today_start,
            UsageEvent.started_at < today_end,
        ).scalar_subquery().label("usage_seconds"),
    ))).one()

    return dict(
        total_children=row.total_children,
        total_active_rules=row.total_active_rules,
        tans_today=row.tans_today,
        total_usage_today_minutes=row.usage_seconds // 60,
    )


# ---------------------------------------------------------------------------
# Child dashboard
# ---------------------------------------------------------------------------

async def get_child_dashboard_stats(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> dict:
    """Get real-time stats for one child.

    Combines 6 scalar lookups into a single DB roundtrip.
    Streak and top-group remain separate (GROUP BY / JOIN logic).
    """

    today_start, today_end = _day_bounds(date.today())
    now = datetime.now(timezone.utc)
    five_minutes_ago = now - timedelta(minutes=5)

    # --- 6 metrics in one roundtrip via scalar subqueries ---
    row = (await db.execute(select(
        select(User.name).where(User.id == child_id)
            .scalar_subquery().label("child_name"),
        select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0)).where(
            UsageEvent.child_id == child_id,
            UsageEvent.started_at >= today_start,
            UsageEvent.started_at < today_end,
        ).scalar_subquery().label("usage_seconds"),
        select(func.min(TimeRule.daily_limit_minutes)).where(
            TimeRule.child_id == child_id,
            TimeRule.active.is_(True),
        ).scalar_subquery().label("daily_limit_minutes"),
        select(func.count()).select_from(TAN).where(
            TAN.child_id == child_id,
            TAN.status == "active",
        ).scalar_subquery().label("active_tans"),
        select(func.count()).select_from(QuestInstance).where(
            QuestInstance.child_id == child_id,
            QuestInstance.status == "approved",
            QuestInstance.reviewed_at >= today_start,
            QuestInstance.reviewed_at < today_end,
        ).scalar_subquery().label("quests_completed_today"),
        select(func.count()).select_from(Device).where(
            Device.child_id == child_id,
            Device.last_seen >= five_minutes_ago,
        ).scalar_subquery().label("devices_online"),
    ))).one()

    child_name: str = row.child_name
    usage_today_seconds: int = row.usage_seconds
    daily_limit_minutes: int | None = row.daily_limit_minutes
    active_tans: int = row.active_tans
    quests_completed_today: int = row.quests_completed_today
    devices_online: int = row.devices_online

    # --- current streak (consecutive days with approved quests) ---
    current_streak = await _compute_quest_streak(db, child_id)

    # --- top group today ---
    top_group_q = (
        select(AppGroup.name, func.sum(UsageEvent.duration_seconds).label("total"))
        .join(AppGroup, UsageEvent.app_group_id == AppGroup.id)
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.started_at >= today_start,
                UsageEvent.started_at < today_end,
            ),
        )
        .group_by(AppGroup.name)
        .order_by(func.sum(UsageEvent.duration_seconds).desc())
        .limit(1)
    )
    top_group_result = await db.execute(top_group_q)
    top_row = top_group_result.first()
    top_group: str | None = top_row[0] if top_row else None

    return dict(
        child_id=child_id,
        child_name=child_name,
        usage_today_minutes=usage_today_seconds // 60,
        daily_limit_minutes=daily_limit_minutes,
        active_tans=active_tans,
        quests_completed_today=quests_completed_today,
        current_streak=current_streak,
        devices_online=devices_online,
        top_group=top_group,
    )


async def _compute_quest_streak(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> int:
    """Count consecutive days (up to today) that have at least one approved quest."""

    # Fetch distinct dates with approved quests, ordered descending
    q = (
        select(func.date(QuestInstance.reviewed_at).label("quest_date"))
        .where(
            and_(
                QuestInstance.child_id == child_id,
                QuestInstance.status == "approved",
                QuestInstance.reviewed_at.is_not(None),
            ),
        )
        .group_by(func.date(QuestInstance.reviewed_at))
        .order_by(func.date(QuestInstance.reviewed_at).desc())
    )
    result = await db.execute(q)
    quest_dates: list[date] = [row[0] for row in result.all()]

    if not quest_dates:
        return 0

    streak = 0
    expected = date.today()
    for d in quest_dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    return streak


# ---------------------------------------------------------------------------
# Full analytics / report
# ---------------------------------------------------------------------------

async def get_child_analytics(
    db: AsyncSession,
    child_id: uuid.UUID,
    period: str,
    start_date: date,
    end_date: date,
) -> dict:
    """Get detailed analytics for a child over a date range."""

    range_start, range_end = _period_bounds(start_date, end_date)

    # --- child name ---
    child_q = select(User.name).where(User.id == child_id)
    child_result = await db.execute(child_q)
    child_name: str = child_result.scalar_one()

    # --- build daily summaries ---
    daily_summaries = await _build_daily_summaries(
        db, child_id, start_date, end_date, range_start, range_end,
    )

    # --- heatmap ---
    heatmap = await _build_heatmap(db, child_id, range_start, range_end)

    # --- weekly trends ---
    trends = await _build_weekly_trends(db, child_id, range_start, range_end)

    # --- overall group breakdown ---
    group_breakdown = await _build_group_breakdown(
        db, child_id, range_start, range_end,
    )

    return dict(
        child_id=child_id,
        child_name=child_name,
        period=period,
        daily_summaries=daily_summaries,
        heatmap=heatmap,
        trends=trends,
        group_breakdown=group_breakdown,
    )


# ---- daily summaries ----

async def _build_daily_summaries(
    db: AsyncSession,
    child_id: uuid.UUID,
    start_date: date,
    end_date: date,
    range_start: datetime,
    range_end: datetime,
) -> list[dict]:
    """Build a list of per-day summary dicts."""

    # Pre-fetch all usage events in the range
    usage_q = (
        select(
            func.date(UsageEvent.started_at).label("day"),
            UsageEvent.app_group_id,
            func.coalesce(func.sum(UsageEvent.duration_seconds), 0).label("seconds"),
        )
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.started_at >= range_start,
                UsageEvent.started_at < range_end,
            ),
        )
        .group_by(func.date(UsageEvent.started_at), UsageEvent.app_group_id)
    )
    usage_result = await db.execute(usage_q)
    usage_rows = usage_result.all()

    # Blocked attempts per day
    blocked_q = (
        select(
            func.date(UsageEvent.started_at).label("day"),
            func.count().label("cnt"),
        )
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.event_type == "blocked",
                UsageEvent.started_at >= range_start,
                UsageEvent.started_at < range_end,
            ),
        )
        .group_by(func.date(UsageEvent.started_at))
    )
    blocked_result = await db.execute(blocked_q)
    blocked_map: dict[date, int] = {row.day: row.cnt for row in blocked_result.all()}

    # Quests completed per day
    quests_q = (
        select(
            func.date(QuestInstance.reviewed_at).label("day"),
            func.count().label("cnt"),
        )
        .where(
            and_(
                QuestInstance.child_id == child_id,
                QuestInstance.status == "approved",
                QuestInstance.reviewed_at >= range_start,
                QuestInstance.reviewed_at < range_end,
            ),
        )
        .group_by(func.date(QuestInstance.reviewed_at))
    )
    quests_result = await db.execute(quests_q)
    quests_map: dict[date, int] = {row.day: row.cnt for row in quests_result.all()}

    # TANs redeemed per day
    tans_q = (
        select(
            func.date(TAN.redeemed_at).label("day"),
            func.count().label("cnt"),
        )
        .where(
            and_(
                TAN.child_id == child_id,
                TAN.status == "redeemed",
                TAN.redeemed_at >= range_start,
                TAN.redeemed_at < range_end,
            ),
        )
        .group_by(func.date(TAN.redeemed_at))
    )
    tans_result = await db.execute(tans_q)
    tans_map: dict[date, int] = {row.day: row.cnt for row in tans_result.all()}

    # Map app_group_id -> name (pre-fetch)
    group_ids = {row.app_group_id for row in usage_rows if row.app_group_id is not None}
    group_name_map: dict[uuid.UUID, str] = {}
    if group_ids:
        gn_q = select(AppGroup.id, AppGroup.name).where(AppGroup.id.in_(group_ids))
        gn_result = await db.execute(gn_q)
        group_name_map = {row.id: row.name for row in gn_result.all()}

    # Organize usage by day
    day_group_seconds: dict[date, dict[uuid.UUID | None, int]] = defaultdict(
        lambda: defaultdict(int),
    )
    for row in usage_rows:
        day_group_seconds[row.day][row.app_group_id] += row.seconds

    # Build summaries
    summaries: list[dict] = []
    current = start_date
    while current <= end_date:
        groups = day_group_seconds.get(current, {})
        total_seconds = sum(groups.values())
        total_minutes = total_seconds // 60

        group_breakdown: list[dict] = []
        for gid, secs in groups.items():
            mins = secs // 60
            pct = (secs / total_seconds * 100) if total_seconds > 0 else 0.0
            group_breakdown.append(
                dict(
                    app_group_id=gid,
                    group_name=group_name_map.get(gid, "Ungrouped") if gid else "Ungrouped",
                    minutes=mins,
                    percentage=round(pct, 1),
                ),
            )
        # Sort by minutes descending
        group_breakdown.sort(key=lambda g: g["minutes"], reverse=True)

        summaries.append(
            dict(
                date=current,
                total_minutes=total_minutes,
                group_breakdown=group_breakdown,
                quests_completed=quests_map.get(current, 0),
                tans_redeemed=tans_map.get(current, 0),
                blocked_attempts=blocked_map.get(current, 0),
            ),
        )
        current += timedelta(days=1)

    return summaries


# ---- heatmap ----

async def _build_heatmap(
    db: AsyncSession,
    child_id: uuid.UUID,
    range_start: datetime,
    range_end: datetime,
) -> list[dict]:
    """Aggregate usage by hour-of-day and day-of-week."""

    # PostgreSQL extract('dow', ...) returns 0=Sun, 6=Sat.
    # We convert to 0=Mon, 6=Sun in Python.
    q = (
        select(
            extract("hour", UsageEvent.started_at).label("hour"),
            extract("dow", UsageEvent.started_at).label("dow"),
            func.coalesce(func.sum(UsageEvent.duration_seconds), 0).label("seconds"),
        )
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.started_at >= range_start,
                UsageEvent.started_at < range_end,
            ),
        )
        .group_by(
            extract("hour", UsageEvent.started_at),
            extract("dow", UsageEvent.started_at),
        )
    )
    result = await db.execute(q)
    entries: list[dict] = []
    for row in result.all():
        # Convert PG dow (0=Sun) to ISO-style (0=Mon, 6=Sun)
        pg_dow = int(row.dow)
        iso_day = (pg_dow - 1) % 7  # Mon=0 .. Sun=6
        entries.append(
            dict(
                hour=int(row.hour),
                day=iso_day,
                minutes=round(row.seconds / 60, 1),
            ),
        )
    return entries


# ---- weekly trends ----

async def _build_weekly_trends(
    db: AsyncSession,
    child_id: uuid.UUID,
    range_start: datetime,
    range_end: datetime,
) -> list[dict]:
    """Aggregate totals per ISO week within the range."""

    # Usage per week
    week_trunc = func.date_trunc(literal_column("'week'"), UsageEvent.started_at)
    usage_q = (
        select(
            week_trunc.label("week"),
            func.coalesce(func.sum(UsageEvent.duration_seconds), 0).label("seconds"),
        )
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.started_at >= range_start,
                UsageEvent.started_at < range_end,
            ),
        )
        .group_by(week_trunc)
        .order_by(week_trunc)
    )
    usage_result = await db.execute(usage_q)
    usage_weeks: dict[date, int] = {}
    for row in usage_result.all():
        week_date = row.week.date() if isinstance(row.week, datetime) else row.week
        usage_weeks[week_date] = row.seconds

    # Quests per week
    quest_week_trunc = func.date_trunc(literal_column("'week'"), QuestInstance.reviewed_at)
    quests_q = (
        select(
            quest_week_trunc.label("week"),
            func.count().label("cnt"),
        )
        .where(
            and_(
                QuestInstance.child_id == child_id,
                QuestInstance.status == "approved",
                QuestInstance.reviewed_at >= range_start,
                QuestInstance.reviewed_at < range_end,
            ),
        )
        .group_by(quest_week_trunc)
    )
    quests_result = await db.execute(quests_q)
    quests_weeks: dict[date, int] = {}
    for row in quests_result.all():
        week_date = row.week.date() if isinstance(row.week, datetime) else row.week
        quests_weeks[week_date] = row.cnt

    # TANs redeemed per week
    tan_week_trunc = func.date_trunc(literal_column("'week'"), TAN.redeemed_at)
    tans_q = (
        select(
            tan_week_trunc.label("week"),
            func.count().label("cnt"),
        )
        .where(
            and_(
                TAN.child_id == child_id,
                TAN.status == "redeemed",
                TAN.redeemed_at >= range_start,
                TAN.redeemed_at < range_end,
            ),
        )
        .group_by(tan_week_trunc)
    )
    tans_result = await db.execute(tans_q)
    tans_weeks: dict[date, int] = {}
    for row in tans_result.all():
        week_date = row.week.date() if isinstance(row.week, datetime) else row.week
        tans_weeks[week_date] = row.cnt

    # Merge all weeks
    all_weeks = sorted(set(usage_weeks) | set(quests_weeks) | set(tans_weeks))
    trends: list[dict] = []
    for w in all_weeks:
        trends.append(
            dict(
                week_start=w,
                total_minutes=usage_weeks.get(w, 0) // 60,
                quests_completed=quests_weeks.get(w, 0),
                tans_redeemed=tans_weeks.get(w, 0),
            ),
        )
    return trends


# ---- group breakdown (overall) ----

async def _build_group_breakdown(
    db: AsyncSession,
    child_id: uuid.UUID,
    range_start: datetime,
    range_end: datetime,
) -> list[dict]:
    """Overall percentage split by app group across the full range."""

    q = (
        select(
            UsageEvent.app_group_id,
            func.coalesce(func.sum(UsageEvent.duration_seconds), 0).label("seconds"),
        )
        .where(
            and_(
                UsageEvent.child_id == child_id,
                UsageEvent.started_at >= range_start,
                UsageEvent.started_at < range_end,
            ),
        )
        .group_by(UsageEvent.app_group_id)
    )
    result = await db.execute(q)
    rows = result.all()

    total_seconds = sum(row.seconds for row in rows)

    # Map group ids to names
    group_ids = {row.app_group_id for row in rows if row.app_group_id is not None}
    group_name_map: dict[uuid.UUID, str] = {}
    if group_ids:
        gn_q = select(AppGroup.id, AppGroup.name).where(AppGroup.id.in_(group_ids))
        gn_result = await db.execute(gn_q)
        group_name_map = {r.id: r.name for r in gn_result.all()}

    breakdown: list[dict] = []
    for row in rows:
        pct = (row.seconds / total_seconds * 100) if total_seconds > 0 else 0.0
        breakdown.append(
            dict(
                app_group_id=row.app_group_id,
                group_name=group_name_map.get(row.app_group_id, "Ungrouped")
                if row.app_group_id
                else "Ungrouped",
                minutes=row.seconds // 60,
                percentage=round(pct, 1),
            ),
        )
    breakdown.sort(key=lambda g: g["minutes"], reverse=True)
    return breakdown
