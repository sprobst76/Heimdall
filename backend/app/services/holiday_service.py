"""Holiday Service.

Fetches public and school holidays from the OpenHolidays API and
creates DayTypeOverride entries in the database.
"""

from datetime import date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.day_type import DayTypeOverride


async def fetch_holidays(
    year: int,
    subdivision: str = "DE-BW",
) -> list[dict]:
    """Fetch public holidays from the OpenHolidays API.

    Args:
        year: The year to fetch holidays for.
        subdivision: The subdivision code (default DE-BW for Baden-Wuerttemberg).

    Returns:
        List of holiday dicts from the API.
    """
    url = (
        f"{settings.HOLIDAY_API_BASE_URL}/PublicHolidays"
        f"?countryIsoCode={settings.HOLIDAY_COUNTRY}"
        f"&languageIsoCode=DE"
        f"&validFrom={year}-01-01"
        f"&validTo={year}-12-31"
        f"&subdivisionCode={subdivision}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_school_holidays(
    year: int,
    subdivision: str = "DE-BW",
) -> list[dict]:
    """Fetch school holidays from the OpenHolidays API.

    Args:
        year: The year to fetch school holidays for.
        subdivision: The subdivision code (default DE-BW for Baden-Wuerttemberg).

    Returns:
        List of school holiday dicts from the API.
    """
    url = (
        f"{settings.HOLIDAY_API_BASE_URL}/SchoolHolidays"
        f"?countryIsoCode={settings.HOLIDAY_COUNTRY}"
        f"&languageIsoCode=DE"
        f"&validFrom={year}-01-01"
        f"&validTo={year}-12-31"
        f"&subdivisionCode={subdivision}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def _extract_holiday_name(holiday: dict) -> str:
    """Extract the German name from a holiday API response entry."""
    names = holiday.get("name", [])
    if isinstance(names, list):
        for name_entry in names:
            if isinstance(name_entry, dict) and name_entry.get("language") == "DE":
                return name_entry.get("text", "Holiday")
        # Fall back to the first name if no German one is found
        if names and isinstance(names[0], dict):
            return names[0].get("text", "Holiday")
    return "Holiday"


def _date_range(start: date, end: date):
    """Yield all dates between start and end (inclusive)."""
    from datetime import timedelta

    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


async def sync_holidays_to_db(
    db: AsyncSession,
    family_id: "uuid.UUID",  # noqa: F821
    year: int,
    subdivision: str = "DE-BW",
) -> list[DayTypeOverride]:
    """Fetch holidays and school holidays, then create DayTypeOverride entries.

    Skips dates that already have an override for this family.

    Args:
        db: Async database session.
        family_id: The family to create overrides for.
        year: The year to sync.
        subdivision: The subdivision code.

    Returns:
        List of newly created DayTypeOverride objects.
    """
    import uuid as _uuid  # noqa: F811

    # Fetch both holiday types concurrently
    public_holidays = await fetch_holidays(year, subdivision)
    school_holidays = await fetch_school_holidays(year, subdivision)

    created: list[DayTypeOverride] = []

    # Process public holidays (single-day events)
    for holiday in public_holidays:
        holiday_date_str = holiday.get("startDate")
        if not holiday_date_str:
            continue

        holiday_date = date.fromisoformat(holiday_date_str)
        label = _extract_holiday_name(holiday)

        # Check if override already exists
        existing = await db.execute(
            select(DayTypeOverride).where(
                DayTypeOverride.family_id == family_id,
                DayTypeOverride.date == holiday_date,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        override = DayTypeOverride(
            family_id=family_id,
            date=holiday_date,
            day_type="holiday",
            label=label,
            source="api",
        )
        db.add(override)
        created.append(override)

    # Process school holidays (date ranges)
    for holiday in school_holidays:
        start_str = holiday.get("startDate")
        end_str = holiday.get("endDate")
        if not start_str or not end_str:
            continue

        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
        label = _extract_holiday_name(holiday)

        for day in _date_range(start_date, end_date):
            # Check if override already exists
            existing = await db.execute(
                select(DayTypeOverride).where(
                    DayTypeOverride.family_id == family_id,
                    DayTypeOverride.date == day,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            override = DayTypeOverride(
                family_id=family_id,
                date=day,
                day_type="vacation",
                label=label,
                source="api",
            )
            db.add(override)
            created.append(override)

    await db.flush()
    for item in created:
        await db.refresh(item)

    return created
