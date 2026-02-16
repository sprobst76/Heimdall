"""Add subject, estimated_minutes, difficulty, checklist_items to quest_templates.

Revision ID: 004
Revises: 003
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quest_templates", sa.Column("subject", sa.String(50), nullable=True))
    op.add_column("quest_templates", sa.Column("estimated_minutes", sa.Integer(), nullable=True))
    op.add_column("quest_templates", sa.Column("difficulty", sa.String(20), nullable=True))
    op.add_column("quest_templates", sa.Column("checklist_items", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("quest_templates", "checklist_items")
    op.drop_column("quest_templates", "difficulty")
    op.drop_column("quest_templates", "estimated_minutes")
    op.drop_column("quest_templates", "subject")
