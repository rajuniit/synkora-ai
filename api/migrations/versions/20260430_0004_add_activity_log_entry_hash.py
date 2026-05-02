"""add entry_hash column to activity_logs

Revision ID: 20260430_0004
Revises: 20260426_0001
Create Date: 2026-04-30 00:04:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0004"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activity_logs", sa.Column("entry_hash", sa.String(64), nullable=True))
    op.create_index("ix_activity_logs_entry_hash", "activity_logs", ["entry_hash"])


def downgrade() -> None:
    op.drop_index("ix_activity_logs_entry_hash", table_name="activity_logs")
    op.drop_column("activity_logs", "entry_hash")
