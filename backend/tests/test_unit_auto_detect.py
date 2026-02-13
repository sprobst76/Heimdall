"""Tests for auto-detect quest completion."""

import uuid
from datetime import datetime, timezone

import pytest

from app.models.quest import QuestInstance, QuestTemplate
from app.models.usage import UsageEvent
from app.models.user import User
from app.services.quest_service import check_auto_detect_quests


async def _create_child(db, family_id):
    child = User(
        family_id=family_id,
        name="Auto-Kind",
        role="child",
    )
    db.add(child)
    await db.flush()
    return child


async def _create_auto_detect_template(db, family_id, app_package="com.mathe.arena", minutes=20):
    template = QuestTemplate(
        family_id=family_id,
        name="Mathe-Training",
        category="learning",
        reward_minutes=15,
        proof_type="auto",
        recurrence="daily",
        auto_detect_app=app_package,
        auto_detect_minutes=minutes,
    )
    db.add(template)
    await db.flush()
    return template


class TestAutoDetect:
    async def test_auto_detect_triggers_on_threshold(self, db_session, registered_parent):
        """Quest auto-approved when usage meets threshold."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        template = await _create_auto_detect_template(db_session, family_id)

        # Assign quest to child
        instance = QuestInstance(
            template_id=template.id,
            child_id=child.id,
            status="available",
        )
        db_session.add(instance)

        # Usage: 25 minutes (above 20 min threshold)
        now = datetime.now(timezone.utc)
        db_session.add(UsageEvent(
            device_id=uuid.uuid4(),  # dummy device
            child_id=child.id,
            app_package="com.mathe.arena",
            event_type="update",
            duration_seconds=1500,  # 25 min
            started_at=now,
        ))
        await db_session.flush()

        approved = await check_auto_detect_quests(
            db_session, child.id, "com.mathe.arena"
        )

        assert len(approved) == 1
        assert approved[0].status == "approved"
        assert approved[0].proof_type == "auto"
        assert approved[0].generated_tan_id is not None

    async def test_auto_detect_below_threshold(self, db_session, registered_parent):
        """Quest stays open when usage below threshold."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        template = await _create_auto_detect_template(db_session, family_id, minutes=20)

        instance = QuestInstance(
            template_id=template.id,
            child_id=child.id,
            status="available",
        )
        db_session.add(instance)

        now = datetime.now(timezone.utc)
        db_session.add(UsageEvent(
            device_id=uuid.uuid4(),
            child_id=child.id,
            app_package="com.mathe.arena",
            event_type="update",
            duration_seconds=900,  # 15 min < 20 min threshold
            started_at=now,
        ))
        await db_session.flush()

        approved = await check_auto_detect_quests(
            db_session, child.id, "com.mathe.arena"
        )

        assert len(approved) == 0

    async def test_auto_detect_no_matching_quest(self, db_session, registered_parent):
        """No auto-detect if no matching template."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)

        now = datetime.now(timezone.utc)
        db_session.add(UsageEvent(
            device_id=uuid.uuid4(),
            child_id=child.id,
            app_package="com.random.app",
            event_type="update",
            duration_seconds=3600,
            started_at=now,
        ))
        await db_session.flush()

        approved = await check_auto_detect_quests(
            db_session, child.id, "com.random.app"
        )

        assert len(approved) == 0

    async def test_auto_detect_already_approved(self, db_session, registered_parent):
        """Already approved quest should not be re-approved."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child = await _create_child(db_session, family_id)
        template = await _create_auto_detect_template(db_session, family_id)

        now = datetime.now(timezone.utc)
        instance = QuestInstance(
            template_id=template.id,
            child_id=child.id,
            status="approved",
            reviewed_at=now,
        )
        db_session.add(instance)

        db_session.add(UsageEvent(
            device_id=uuid.uuid4(),
            child_id=child.id,
            app_package="com.mathe.arena",
            event_type="update",
            duration_seconds=3600,
            started_at=now,
        ))
        await db_session.flush()

        approved = await check_auto_detect_quests(
            db_session, child.id, "com.mathe.arena"
        )

        assert len(approved) == 0
