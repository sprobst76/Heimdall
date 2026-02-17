"""Create tan_schedules and tan_schedule_logs tables.

Revision ID: 006
Revises: 005
Create Date: 2026-02-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tan_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("child_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("recurrence", sa.String(20), nullable=False),
        sa.Column("tan_type", sa.String(30), nullable=False),
        sa.Column("value_minutes", sa.Integer(), nullable=True),
        sa.Column("value_unlock_until", sa.Time(), nullable=True),
        sa.Column("scope_groups", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("scope_devices", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("expires_after_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tan_schedule_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("tan_schedules.id"), nullable=False),
        sa.Column("generated_date", sa.Date(), nullable=False),
        sa.Column("generated_tan_id", sa.Uuid(), sa.ForeignKey("tans.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("schedule_id", "generated_date", name="uq_tan_schedule_log_date"),
    )


def downgrade() -> None:
    op.drop_table("tan_schedule_logs")
    op.drop_table("tan_schedules")
