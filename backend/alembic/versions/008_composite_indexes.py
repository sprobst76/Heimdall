"""Add composite indexes for dashboard and analytics queries.

Revision ID: 008
Revises: 007
Create Date: 2026-02-19
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # UsageEvent: dashboard usage-today + analytics range queries
    op.create_index("ix_usage_events_child_started", "usage_events", ["child_id", "started_at"])

    # TAN: active-TAN count + today's TAN count
    op.create_index("ix_tans_child_status", "tans", ["child_id", "status"])
    op.create_index("ix_tans_child_created", "tans", ["child_id", "created_at"])

    # QuestInstance: approved-today count + streak calculation
    op.create_index(
        "ix_quest_inst_child_status_rev",
        "quest_instances",
        ["child_id", "status", "reviewed_at"],
    )

    # Device: devices-online count (last_seen within 5 minutes)
    op.create_index("ix_devices_child_seen", "devices", ["child_id", "last_seen"])

    # TimeRule: active rules for rule engine
    op.create_index("ix_time_rules_child_active", "time_rules", ["child_id", "active"])


def downgrade() -> None:
    op.drop_index("ix_time_rules_child_active", "time_rules")
    op.drop_index("ix_devices_child_seen", "devices")
    op.drop_index("ix_quest_inst_child_status_rev", "quest_instances")
    op.drop_index("ix_tans_child_created", "tans")
    op.drop_index("ix_tans_child_status", "tans")
    op.drop_index("ix_usage_events_child_started", "usage_events")
