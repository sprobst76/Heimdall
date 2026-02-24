"""Rule Engine Service (Phase 1).

Resolves the currently active rules for a device based on:
- The child assigned to the device
- Today's day type (with override support)
- Active time rules matching the day type
- Currently active TANs
"""

import json
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis

RULES_CACHE_TTL = 30  # seconds

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
    bypass_cache: bool = False,
) -> dict:
    """Resolve the currently active rules for a device.

    Returns the cached result if available (TTL 30s), unless bypass_cache=True.
    Use bypass_cache=True when pushing rules after a mutation so the cache is
    refreshed immediately.
    """
    cache_key = f"rules:device:{device_id}"
    redis = await get_redis()

    if not bypass_cache and redis is not None:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

    result = await _compute_current_rules(db, device_id)

    if redis is not None:
        await redis.setex(cache_key, RULES_CACHE_TTL, json.dumps(result, default=str))

    return result


async def _compute_current_rules(
    db: AsyncSession,
    device_id: uuid.UUID,
) -> dict:
    """Compute the currently active rules for a device (no caching).

    Steps:
    1. Get device and child
    2. Check for device coupling (shared budget)
    3. Determine today's day type
    4. Get all active TimeRules for the child matching the day type
    5. Sort by priority (highest first)
    6. Calculate usage (considering coupled devices if shared_budget)
    7. Get active TANs
    8. Return resolved rules dict
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

    # 4. Get active TimeRules valid for today (date range filtered in SQL)
    rules_result = await db.execute(
        select(TimeRule).where(
            TimeRule.child_id == child_id,
            TimeRule.active == True,  # noqa: E712
            or_(TimeRule.valid_from.is_(None), TimeRule.valid_from <= today),
            or_(TimeRule.valid_until.is_(None), TimeRule.valid_until >= today),
        )
    )
    all_rules = rules_result.scalars().all()

    # day_types is a JSON array — filter in Python (DB-agnostic)
    matching_rules = [r for r in all_rules if day_type in (r.day_types or [])]

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
    totp_config = None
    if child.totp_enabled and child.totp_secret:
        totp_config = {
            "enabled": True,
            "secret": child.totp_secret,
            "mode": child.totp_mode,
            "tan_minutes": child.totp_tan_minutes,
            "override_minutes": child.totp_override_minutes,
        }

    return {
        "day_type": day_type,
        "time_windows": time_windows,
        "group_limits": group_limits,
        "daily_limit_minutes": daily_limit_minutes,
        "remaining_minutes": remaining_minutes,
        "active_tans": tan_list,
        "coupled_devices": coupled_devices,
        "shared_budget": shared_budget,
        "totp_config": totp_config,
    }
