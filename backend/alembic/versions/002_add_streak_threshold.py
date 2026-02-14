"""Add streak_threshold to quest_templates.

Revision ID: 002
Revises: 001
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add streak_threshold column to quest_templates."""
    op.add_column(
        "quest_templates",
        sa.Column("streak_threshold", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove streak_threshold column."""
    op.drop_column("quest_templates", "streak_threshold")
