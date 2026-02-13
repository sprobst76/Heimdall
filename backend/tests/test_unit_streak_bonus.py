"""Tests for streak bonus quest system."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.quest import QuestInstance, QuestTemplate
from app.models.user import User
from app.services.quest_service import check_streak_bonus


async def _create_child(db, family_id):
    child = User(
        family_id=family_id,
        name="Streak-Kind",
        role="child",
    )
    db.add(child)
    await db.flush()
    return child


async def _create_streak_template(db, family_id, threshold=5, reward=60):
    template = QuestTemplate(
        family_id=family_id,
        name="Wochen-Champion",
        category="streak",
        reward_minutes=reward,
        proof_type="auto",
        recurrence="daily",
        streak_threshold=threshold,
    )
    db.add(template)
    await db.flush()
    return template


async def _create_streak_history(db, child, family_id, days):
    """Create approved quest instances for consecutive days ending today."""
    now = datetime.now(timezone.utc)
    # Need a regular (non-streak) template for the daily quests
    daily_template = QuestTemplate(
        family_id=family_id,
        name="Tägliche Aufgabe",
        category="household",
        reward_minutes=15,
        proof_type="parent_confirm",
        recurrence="daily",
    )
    db.add(daily_template)
    await db.flush()

    for i in range(days):
        day = now - timedelta(days=i)
        instance = QuestInstance(
            template_id=daily_template.id,
            child_id=child.id,
            status="approved",
            claimed_at=day,
            reviewed_at=day,
        )
        db.add(instance)

    await db.flush()


class TestStreakBonus:
    async def test_streak_bonus_at_threshold(self, db_session, registered_parent):
        """5-day streak should trigger bonus quest with 60 min TAN."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        template = await _create_streak_template(db_session, family_id, threshold=5, reward=60)
        await _create_streak_history(db_session, child, family_id, days=5)

        bonus = await check_streak_bonus(db_session, child.id)

        assert bonus is not None
        assert bonus.status == "approved"
        assert bonus.template_id == template.id
        assert bonus.generated_tan_id is not None

    async def test_streak_bonus_below_threshold(self, db_session, registered_parent):
        """3-day streak with 5-day threshold should not trigger bonus."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        await _create_streak_template(db_session, family_id, threshold=5)
        await _create_streak_history(db_session, child, family_id, days=3)

        bonus = await check_streak_bonus(db_session, child.id)

        assert bonus is None

    async def test_streak_bonus_not_duplicated(self, db_session, registered_parent):
        """Bonus should only be awarded once per day."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        template = await _create_streak_template(db_session, family_id, threshold=3)
        await _create_streak_history(db_session, child, family_id, days=5)

        # First call: should award bonus
        bonus1 = await check_streak_bonus(db_session, child.id)
        assert bonus1 is not None

        # Second call: should NOT award again
        bonus2 = await check_streak_bonus(db_session, child.id)
        assert bonus2 is None

    async def test_streak_bonus_no_template(self, db_session, registered_parent):
        """Without streak template, no bonus even with long streak."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        await _create_streak_history(db_session, child, family_id, days=10)

        bonus = await check_streak_bonus(db_session, child.id)

        assert bonus is None
