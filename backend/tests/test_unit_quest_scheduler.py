"""Tests for automatic quest scheduling."""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models.day_type import DayTypeOverride
from app.models.quest import QuestInstance, QuestTemplate
from app.models.user import User
from app.services.quest_scheduler import _get_day_info, _should_schedule, schedule_daily_quests


async def _create_child(db, family_id, name="Test-Kind"):
    child = User(
        family_id=family_id,
        name=name,
        role="child",
    )
    db.add(child)
    await db.flush()
    return child


async def _create_template(db, family_id, recurrence="daily", active=True, **kwargs):
    template = QuestTemplate(
        family_id=family_id,
        name=kwargs.get("name", f"Quest-{recurrence}"),
        category="household",
        reward_minutes=15,
        proof_type="parent_confirm",
        recurrence=recurrence,
        active=active,
    )
    db.add(template)
    await db.flush()
    return template


class TestGetDayInfo:
    async def test_weekday(self, db_session, registered_parent):
        """Monday-Friday returns is_weekday=True."""
        family_id = uuid.UUID(registered_parent["family_id"])

        # Find a weekday (Monday)
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        info = await _get_day_info(db_session, family_id, monday)
        assert info["is_weekday"] is True
        assert info["is_school_day"] is True

    async def test_weekend(self, db_session, registered_parent):
        """Saturday/Sunday returns is_weekday=False."""
        family_id = uuid.UUID(registered_parent["family_id"])

        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)

        info = await _get_day_info(db_session, family_id, saturday)
        assert info["is_weekday"] is False
        assert info["is_school_day"] is False

    async def test_holiday_on_weekday(self, db_session, registered_parent):
        """Holiday override on a weekday → is_school_day=False."""
        family_id = uuid.UUID(registered_parent["family_id"])

        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # Add holiday override
        override = DayTypeOverride(
            family_id=family_id,
            date=monday,
            day_type="holiday",
            label="Feiertag",
            source="manual",
        )
        db_session.add(override)
        await db_session.flush()

        info = await _get_day_info(db_session, family_id, monday)
        assert info["is_weekday"] is True
        assert info["is_holiday"] is True
        assert info["is_school_day"] is False


class TestShouldSchedule:
    def test_daily_always(self):
        """Daily templates always schedule."""
        template = QuestTemplate(recurrence="daily", created_at=datetime.now(timezone.utc))
        assert _should_schedule(template, {"is_school_day": True}, date.today()) is True
        assert _should_schedule(template, {"is_school_day": False}, date.today()) is True

    def test_school_days_on_school_day(self):
        """school_days template schedules on school days."""
        template = QuestTemplate(recurrence="school_days", created_at=datetime.now(timezone.utc))
        assert _should_schedule(template, {"is_school_day": True}, date.today()) is True

    def test_school_days_not_on_holiday(self):
        """school_days template skips holidays."""
        template = QuestTemplate(recurrence="school_days", created_at=datetime.now(timezone.utc))
        assert _should_schedule(template, {"is_school_day": False}, date.today()) is False

    def test_weekly_correct_day(self):
        """Weekly template schedules on matching weekday."""
        today = date.today()
        # Create template with created_at on today's weekday
        template = QuestTemplate(
            recurrence="weekly",
            created_at=datetime.now(timezone.utc),
        )
        assert _should_schedule(template, {}, today) is True

    def test_weekly_wrong_day(self):
        """Weekly template skips non-matching weekday."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        template = QuestTemplate(
            recurrence="weekly",
            created_at=datetime.now(timezone.utc),
        )
        assert _should_schedule(template, {}, tomorrow) is False

    def test_once_never_scheduled(self):
        """once templates are never auto-scheduled."""
        template = QuestTemplate(recurrence="once", created_at=datetime.now(timezone.utc))
        assert _should_schedule(template, {"is_school_day": True}, date.today()) is False


class TestScheduleDailyQuests:
    async def test_daily_quest_created(self, db_session, registered_parent):
        """Daily template creates instance for each child."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="daily")

        count = await schedule_daily_quests(db_session, family_id)

        assert count == 1

    async def test_no_duplicate_instances(self, db_session, registered_parent):
        """Running scheduler twice doesn't create duplicates."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="daily")

        count1 = await schedule_daily_quests(db_session, family_id)
        count2 = await schedule_daily_quests(db_session, family_id)

        assert count1 == 1
        assert count2 == 0

    async def test_once_template_skipped(self, db_session, registered_parent):
        """once templates are not auto-scheduled."""
        family_id = uuid.UUID(registered_parent["family_id"])
        await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="once")

        count = await schedule_daily_quests(db_session, family_id)
        assert count == 0

    async def test_inactive_template_skipped(self, db_session, registered_parent):
        """Inactive templates are not scheduled."""
        family_id = uuid.UUID(registered_parent["family_id"])
        await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="daily", active=False)

        count = await schedule_daily_quests(db_session, family_id)
        assert count == 0

    async def test_school_days_skipped_on_weekend(self, db_session, registered_parent):
        """school_days quest not created on weekend."""
        family_id = uuid.UUID(registered_parent["family_id"])
        await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="school_days")

        # Mock today as Saturday
        saturday = date.today()
        while saturday.weekday() != 5:  # 5 = Saturday
            saturday += timedelta(days=1)

        with patch("app.services.quest_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.combine(
                saturday, datetime.min.time(), tzinfo=timezone.utc,
            )
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            count = await schedule_daily_quests(db_session, family_id)

        assert count == 0

    async def test_school_days_skipped_on_holiday(self, db_session, registered_parent):
        """school_days quest not created when holiday override exists."""
        family_id = uuid.UUID(registered_parent["family_id"])
        await _create_child(db_session, family_id)
        await _create_template(db_session, family_id, recurrence="school_days")

        # Add holiday for today
        today = datetime.now(timezone.utc).date()
        override = DayTypeOverride(
            family_id=family_id,
            date=today,
            day_type="holiday",
            label="Test-Feiertag",
            source="manual",
        )
        db_session.add(override)
        await db_session.flush()

        # If today is a weekday, the holiday should prevent scheduling
        if today.weekday() < 5:
            count = await schedule_daily_quests(db_session, family_id)
            assert count == 0

    async def test_multiple_children_multiple_templates(self, db_session, registered_parent):
        """Multiple children × templates creates correct instance count."""
        family_id = uuid.UUID(registered_parent["family_id"])
        await _create_child(db_session, family_id, name="Kind-A")
        await _create_child(db_session, family_id, name="Kind-B")
        await _create_template(db_session, family_id, recurrence="daily", name="Quest-1")
        await _create_template(db_session, family_id, recurrence="daily", name="Quest-2")

        count = await schedule_daily_quests(db_session, family_id)

        assert count == 4  # 2 children × 2 templates
