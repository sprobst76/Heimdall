"""Initial schema — all Phase 1-3 tables.

Revision ID: 001
Revises: None
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # ── families ──────────────────────────────────────────────────────
    op.create_table(
        "families",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Europe/Berlin"),
        sa.Column("settings", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("pin_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── refresh_tokens ────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── devices ───────────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("device_identifier", sa.String(255), unique=True, nullable=False),
        sa.Column("device_token_hash", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── device_couplings ──────────────────────────────────────────────
    op.create_table(
        "device_couplings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("shared_budget", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── app_groups ────────────────────────────────────────────────────
    op.create_table(
        "app_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("always_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tan_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_tan_bonus_per_day", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── app_group_apps ────────────────────────────────────────────────
    op.create_table(
        "app_group_apps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("app_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("app_package", sa.String(255), nullable=True),
        sa.Column("app_executable", sa.String(255), nullable=True),
        sa.Column("app_name", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
    )

    # ── time_rules ────────────────────────────────────────────────────
    op.create_table(
        "time_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("day_types", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY['weekday']::text[]")),
        sa.Column("time_windows", postgresql.JSON(), nullable=False),
        sa.Column("daily_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("group_limits", postgresql.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── day_type_overrides ────────────────────────────────────────────
    op.create_table(
        "day_type_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("day_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.UniqueConstraint("family_id", "date", name="uq_day_type_overrides_family_date"),
    )

    # ── tans ──────────────────────────────────────────────────────────
    op.create_table(
        "tans",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("scope_groups", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("scope_devices", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("value_minutes", sa.Integer(), nullable=True),
        sa.Column("value_unlock_until", sa.Time(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("single_use", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_quest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── quest_templates ───────────────────────────────────────────────
    op.create_table(
        "quest_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("reward_minutes", sa.Integer(), nullable=False),
        sa.Column("tan_groups", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("proof_type", sa.String(20), nullable=False),
        sa.Column("ai_verify", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_prompt", sa.Text(), nullable=True),
        sa.Column("recurrence", sa.String(30), nullable=False),
        sa.Column("auto_detect_app", sa.String(255), nullable=True),
        sa.Column("auto_detect_minutes", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── quest_instances ───────────────────────────────────────────────
    op.create_table(
        "quest_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quest_templates.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proof_url", sa.Text(), nullable=True),
        sa.Column("proof_type", sa.String(20), nullable=True),
        sa.Column("ai_result", postgresql.JSON(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_tan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tans.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── usage_events ──────────────────────────────────────────────────
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("app_package", sa.String(255), nullable=True),
        sa.Column("app_group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("app_groups.id"), nullable=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Indexes ───────────────────────────────────────────────────────
    op.create_index("ix_usage_events_child_started", "usage_events", ["child_id", "started_at"])
    op.create_index("ix_usage_events_app_group_started", "usage_events", ["app_group_id", "started_at"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_index("ix_usage_events_app_group_started", table_name="usage_events")
    op.drop_index("ix_usage_events_child_started", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_table("quest_instances")
    op.drop_table("quest_templates")
    op.drop_table("tans")
    op.drop_table("day_type_overrides")
    op.drop_table("time_rules")
    op.drop_table("app_group_apps")
    op.drop_table("app_groups")
    op.drop_table("device_couplings")
    op.drop_table("devices")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("families")
