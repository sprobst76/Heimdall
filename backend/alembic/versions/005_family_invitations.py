"""Create family_invitations table.

Revision ID: 005
Revises: 004
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "family_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="parent"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_invitations_code", "family_invitations", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_family_invitations_code", table_name="family_invitations")
    op.drop_table("family_invitations")
