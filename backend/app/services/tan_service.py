"""TAN Service.

Business logic for TAN code generation, validation, and redemption.
"""

import random
from datetime import datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_group import AppGroup
from app.models.tan import TAN

# Mythological word list for TAN codes
WORD_LIST = [
    "HERO", "ODIN", "THOR", "LOKI", "FREYA", "FENRIR", "BALDUR", "SIGURD",
    "BRAGI", "IDUN", "NORNS", "AEGIR", "SKADI", "FRIGG", "VIDAR", "VALI",
    "MAGNI", "MODI", "NJORD", "TYR",
]

# Default policy limits
DEFAULT_MAX_TANS_PER_DAY = 3
DEFAULT_MAX_BONUS_MINUTES_PER_DAY = 90
BLACKOUT_START = time(21, 0)  # 21:00
BLACKOUT_END = time(6, 0)     # 06:00


def _generate_code() -> str:
    """Generate a TAN code like 'HERO-7749'."""
    word = random.choice(WORD_LIST)
    digits = f"{random.randint(0, 9999):04d}"
    return f"{word}-{digits}"


async def generate_tan_code(db: AsyncSession) -> str:
    """Generate a unique TAN code, retrying if a collision occurs."""
    for _ in range(10):
        code = _generate_code()
        result = await db.execute(select(TAN).where(TAN.code == code))
        if result.scalar_one_or_none() is None:
            return code

    # Extremely unlikely: 10 collisions in a row
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate unique TAN code",
    )


async def validate_tan_redemption(
    db: AsyncSession,
    tan: TAN,
    child_id: "uuid.UUID",  # noqa: F821
) -> None:
    """Validate all policies for TAN redemption.

    Raises HTTPException if any policy is violated.
    """
    import uuid as _uuid  # noqa: F811

    now = datetime.now(timezone.utc)

    # 1. TAN must be active
    if tan.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TAN is not active (current status: {tan.status})",
        )

    # 2. TAN must not be expired
    if tan.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TAN has expired",
        )

    # 3. Daily TAN limit not exceeded
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone.utc)

    redeemed_today_count = await db.execute(
        select(func.count(TAN.id)).where(
            TAN.child_id == child_id,
            TAN.status == "redeemed",
            TAN.redeemed_at >= today_start,
            TAN.redeemed_at <= today_end,
        )
    )
    count = redeemed_today_count.scalar() or 0

    if count >= DEFAULT_MAX_TANS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily TAN limit reached ({DEFAULT_MAX_TANS_PER_DAY} per day)",
        )

    # 4. Daily bonus minutes limit not exceeded
    if tan.value_minutes is not None:
        bonus_today = await db.execute(
            select(func.coalesce(func.sum(TAN.value_minutes), 0)).where(
                TAN.child_id == child_id,
                TAN.status == "redeemed",
                TAN.redeemed_at >= today_start,
                TAN.redeemed_at <= today_end,
                TAN.value_minutes.isnot(None),
            )
        )
        total_bonus = bonus_today.scalar() or 0

        if total_bonus + tan.value_minutes > DEFAULT_MAX_BONUS_MINUTES_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily bonus minutes limit would be exceeded "
                       f"({total_bonus + tan.value_minutes}/{DEFAULT_MAX_BONUS_MINUTES_PER_DAY} min)",
            )

    # 5. Group TAN allowed (check app_group.tan_allowed for scoped groups)
    if tan.scope_groups:
        for group_id in tan.scope_groups:
            result = await db.execute(
                select(AppGroup).where(AppGroup.id == group_id)
            )
            group = result.scalar_one_or_none()
            if group is not None and not group.tan_allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"TANs are not allowed for app group '{group.name}'",
                )

    # 6. Not in blackout hours (21:00 - 06:00)
    current_time = now.time()
    if current_time >= BLACKOUT_START or current_time < BLACKOUT_END:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TANs cannot be redeemed during blackout hours (21:00 - 06:00)",
        )


async def redeem_tan(db: AsyncSession, tan: TAN) -> None:
    """Mark a TAN as redeemed."""
    tan.status = "redeemed"
    tan.redeemed_at = datetime.now(timezone.utc)
    await db.flush()
