"""Add usage_reward_rules and usage_reward_logs tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create usage reward tables."""

    op.create_table(
        "usage_reward_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("target_group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("app_groups.id"), nullable=True),
        sa.Column("streak_days", sa.Integer(), nullable=True),
        sa.Column("reward_minutes", sa.Integer(), nullable=False),
        sa.Column("reward_group_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "usage_reward_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usage_reward_rules.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("evaluated_date", sa.Date(), nullable=False),
        sa.Column("usage_minutes", sa.Integer(), nullable=False),
        sa.Column("threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("rewarded", sa.Boolean(), nullable=False),
        sa.Column("generated_tan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tans.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("rule_id", "evaluated_date", name="uq_reward_log_rule_date"),
    )

    op.create_index("ix_reward_logs_child_date", "usage_reward_logs", ["child_id", "evaluated_date"])


def downgrade() -> None:
    """Drop usage reward tables."""
    op.drop_index("ix_reward_logs_child_date", table_name="usage_reward_logs")
    op.drop_table("usage_reward_logs")
    op.drop_table("usage_reward_rules")
