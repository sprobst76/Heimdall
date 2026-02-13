"""Rule Engine Service (Phase 1).

Resolves the currently active rules for a device based on:
- The child assigned to the device
- Today's day type (with override support)
- Active time rules matching the day type
- Currently active TANs
"""

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func

from app.models.day_type import DayTypeOverride
from app.models.device import Device, DeviceCoupling
from app.models.tan import TAN
from app.models.time_rule import TimeRule
from app.models.usage import UsageEvent
from app.models.user import User


async def get_today_day_type(
    db: AsyncSession,
    family_id: uuid.UUID,
    target_date: date | None = None,
) -> str:
    """Determine the day type for a given date.

    Checks DayTypeOverrides first, then falls back to weekend/weekday
    based on the day of the week.

    Args:
        db: Async database session.
        family_id: The family to check overrides for.
        target_date: The date to check. Defaults to today (UTC).

    Returns:
        Day type string (e.g. 'weekday', 'weekend', 'holiday', 'vacation').
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    # Check for manual / API overrides first
    result = await db.execute(
        select(DayTypeOverride).where(
            DayTypeOverride.family_id == family_id,
            DayTypeOverride.date == target_date,
        )
    )
    override = result.scalar_one_or_none()

    if override is not None:
        return override.day_type

    # Fall back to weekday/weekend
    # Monday = 0, Sunday = 6
    if target_date.weekday() >= 5:
        return "weekend"
    return "weekday"


async def get_current_rules(
    db: AsyncSession,
    device_id: uuid.UUID,
) -> dict:
    """Resolve the currently active rules for a device.

    Steps:
    1. Get device and child
    2. Check for device coupling (shared budget)
    3. Determine today's day type
    4. Get all active TimeRules for the child matching the day type
    5. Sort by priority (highest first)
    6. Calculate usage (considering coupled devices if shared_budget)
    7. Get active TANs
    8. Return resolved rules dict

    Args:
        db: Async database session.
        device_id: The device to resolve rules for.

    Returns:
        Dict with keys: day_type, time_windows, group_limits,
        daily_limit_minutes, remaining_minutes, active_tans,
        coupled_devices, shared_budget.
    """
    empty_result = {
        "day_type": "unknown",
        "time_windows": [],
        "group_limits": [],
        "daily_limit_minutes": None,
        "remaining_minutes": None,
        "active_tans": [],
        "coupled_devices": [],
        "shared_budget": False,
    }

    now = datetime.now(timezone.utc)
    today = now.date()

    # 1. Get device and child
    device_result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = device_result.scalar_one_or_none()

    if device is None:
        return empty_result

    child_id = device.child_id

    child_result = await db.execute(
        select(User).where(User.id == child_id)
    )
    child = child_result.scalar_one_or_none()

    if child is None:
        return empty_result

    # 2. Check for device coupling
    coupling_result = await db.execute(
        select(DeviceCoupling).where(DeviceCoupling.child_id == child_id)
    )
    coupling = coupling_result.scalar_one_or_none()

    coupled_devices: list[str] = []
    shared_budget = False

    if coupling is not None and device_id in (coupling.device_ids or []):
        coupled_devices = [
            str(d) for d in coupling.device_ids if d != device_id
        ]
        shared_budget = coupling.shared_budget

    # 3. Determine today's day type
    day_type = await get_today_day_type(db, child.family_id, today)

    # 4. Get all active TimeRules matching the day type
    rules_result = await db.execute(
        select(TimeRule).where(
            TimeRule.child_id == child_id,
            TimeRule.active == True,  # noqa: E712
        )
    )
    all_rules = rules_result.scalars().all()

    matching_rules = []
    for rule in all_rules:
        if day_type not in (rule.day_types or []):
            continue
        if rule.valid_from is not None and today < rule.valid_from:
            continue
        if rule.valid_until is not None and today > rule.valid_until:
            continue
        matching_rules.append(rule)

    # 5. Sort by priority (highest first)
    matching_rules.sort(key=lambda r: r.priority, reverse=True)

    time_windows: list[dict] = []
    group_limits: list[dict] = []
    daily_limit_minutes: int | None = None

    for rule in matching_rules:
        if rule.time_windows:
            windows = rule.time_windows if isinstance(rule.time_windows, list) else []
            time_windows.extend(windows)

        if rule.group_limits:
            limits = rule.group_limits if isinstance(rule.group_limits, list) else []
            group_limits.extend(limits)

        if rule.daily_limit_minutes is not None:
            if daily_limit_minutes is None:
                daily_limit_minutes = rule.daily_limit_minutes
            else:
                daily_limit_minutes = min(daily_limit_minutes, rule.daily_limit_minutes)

    # 6. Calculate remaining minutes (considering coupled devices)
    remaining_minutes: int | None = None

    if daily_limit_minutes is not None:
        today_start = datetime.combine(today, time(0, 0), tzinfo=timezone.utc)

        # Determine which devices to count usage from
        devices_to_count = [device_id]
        if shared_budget and coupling is not None:
            devices_to_count = list(coupling.device_ids or [])

        usage_result = await db.execute(
            select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0)).where(
                UsageEvent.device_id.in_(devices_to_count),
                UsageEvent.started_at >= today_start,
            )
        )
        total_seconds = usage_result.scalar() or 0
        used_minutes = total_seconds // 60
        remaining_minutes = max(0, daily_limit_minutes - used_minutes)

    # 7. Get active TANs for the child
    tans_result = await db.execute(
        select(TAN).where(
            TAN.child_id == child_id,
            TAN.status == "active",
            TAN.expires_at > now,
        )
    )
    active_tans = tans_result.scalars().all()

    tan_list = [
        {
            "id": str(tan.id),
            "type": tan.type,
            "value_minutes": tan.value_minutes,
            "value_unlock_until": tan.value_unlock_until.isoformat() if tan.value_unlock_until else None,
            "scope_groups": [str(g) for g in tan.scope_groups] if tan.scope_groups else None,
            "scope_devices": [str(d) for d in tan.scope_devices] if tan.scope_devices else None,
            "expires_at": tan.expires_at.isoformat(),
        }
        for tan in active_tans
    ]

    # 8. Return resolved rules
    return {
        "day_type": day_type,
        "time_windows": time_windows,
        "group_limits": group_limits,
        "daily_limit_minutes": daily_limit_minutes,
        "remaining_minutes": remaining_minutes,
        "active_tans": tan_list,
        "coupled_devices": coupled_devices,
        "shared_budget": shared_budget,
    }
