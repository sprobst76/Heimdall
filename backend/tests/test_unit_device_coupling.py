"""Tests for device coupling shared budgets in the rule engine."""

import uuid
from datetime import datetime, timezone

import pytest

from app.models.device import Device, DeviceCoupling
from app.models.time_rule import TimeRule
from app.models.usage import UsageEvent
from app.models.user import User
from app.services.rule_engine import get_current_rules


async def _create_child_and_devices(db, family_id, n_devices=2):
    """Create a child user and N devices. Returns (child, devices)."""
    child = User(
        family_id=family_id,
        name="Test Kind",
        role="child",
    )
    db.add(child)
    await db.flush()

    devices = []
    for i in range(n_devices):
        d = Device(
            child_id=child.id,
            name=f"Device-{i}",
            type="android",
            device_identifier=f"dev-{uuid.uuid4().hex[:8]}",
            device_token_hash=f"hash-{uuid.uuid4().hex[:8]}",
            status="active",
        )
        db.add(d)
        devices.append(d)

    await db.flush()
    return child, devices


class TestSharedBudget:
    async def test_shared_budget_aggregates_usage(self, db_session, registered_parent):
        """Shared budget should sum usage across all coupled devices."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child, (dev_a, dev_b) = await _create_child_and_devices(db_session, family_id)

        # Couple devices with shared budget
        coupling = DeviceCoupling(
            child_id=child.id,
            device_ids=[dev_a.id, dev_b.id],
            shared_budget=True,
        )
        db_session.add(coupling)

        # Create time rule with 120 min daily limit
        rule = TimeRule(
            child_id=child.id,
            name="Test",
            target_type="device",
            day_types=["weekday", "weekend"],
            time_windows=[],
            daily_limit_minutes=120,
            priority=10,
            active=True,
        )
        db_session.add(rule)

        # Usage: 30 min on device A, 20 min on device B
        now = datetime.now(timezone.utc)
        db_session.add(UsageEvent(
            device_id=dev_a.id, child_id=child.id,
            event_type="update", duration_seconds=1800,
            started_at=now,
        ))
        db_session.add(UsageEvent(
            device_id=dev_b.id, child_id=child.id,
            event_type="update", duration_seconds=1200,
            started_at=now,
        ))
        await db_session.flush()

        rules = await get_current_rules(db_session, dev_a.id)

        assert rules["daily_limit_minutes"] == 120
        assert rules["remaining_minutes"] == 70  # 120 - 30 - 20
        assert rules["shared_budget"] is True
        assert str(dev_b.id) in rules["coupled_devices"]

    async def test_independent_budget_no_aggregation(self, db_session, registered_parent):
        """Independent budget should only count the queried device's usage."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child, (dev_a, dev_b) = await _create_child_and_devices(db_session, family_id)

        # Couple devices WITHOUT shared budget
        coupling = DeviceCoupling(
            child_id=child.id,
            device_ids=[dev_a.id, dev_b.id],
            shared_budget=False,
        )
        db_session.add(coupling)

        rule = TimeRule(
            child_id=child.id,
            name="Test",
            target_type="device",
            day_types=["weekday", "weekend"],
            time_windows=[],
            daily_limit_minutes=120,
            priority=10,
            active=True,
        )
        db_session.add(rule)

        now = datetime.now(timezone.utc)
        db_session.add(UsageEvent(
            device_id=dev_a.id, child_id=child.id,
            event_type="update", duration_seconds=1800,
            started_at=now,
        ))
        db_session.add(UsageEvent(
            device_id=dev_b.id, child_id=child.id,
            event_type="update", duration_seconds=3600,
            started_at=now,
        ))
        await db_session.flush()

        rules = await get_current_rules(db_session, dev_a.id)

        # Should only count dev_a usage (30 min)
        assert rules["remaining_minutes"] == 90  # 120 - 30
        assert rules["shared_budget"] is False

    async def test_no_coupling_returns_defaults(self, db_session, registered_parent):
        """Without coupling, coupled_devices should be empty."""
        family_id = uuid.UUID(registered_parent["family_id"])
        child, (dev_a, _) = await _create_child_and_devices(db_session, family_id)

        rule = TimeRule(
            child_id=child.id,
            name="Test",
            target_type="device",
            day_types=["weekday", "weekend"],
            time_windows=[],
            daily_limit_minutes=60,
            priority=10,
            active=True,
        )
        db_session.add(rule)
        await db_session.flush()

        rules = await get_current_rules(db_session, dev_a.id)

        assert rules["coupled_devices"] == []
        assert rules["shared_budget"] is False
        assert rules["remaining_minutes"] == 60  # No usage

    async def test_nonexistent_device_returns_unknown(self, db_session):
        """Nonexistent device should return unknown day_type."""
        rules = await get_current_rules(db_session, uuid.uuid4())
        assert rules["day_type"] == "unknown"
        assert rules["remaining_minutes"] is None
