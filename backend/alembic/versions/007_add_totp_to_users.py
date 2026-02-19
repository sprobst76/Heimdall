"""Add TOTP fields to users table.

Revision ID: 007
Revises: 006
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("totp_mode", sa.String(20), nullable=False, server_default="tan"),
    )
    op.add_column(
        "users",
        sa.Column("totp_tan_minutes", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_override_minutes", sa.Integer(), nullable=False, server_default="30"
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_override_minutes")
    op.drop_column("users", "totp_tan_minutes")
    op.drop_column("users", "totp_mode")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
