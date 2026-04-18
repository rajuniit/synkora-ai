"""fix data_source_sync_jobs started_at and completed_at to timestamp with time zone

Revision ID: 20260418_0003
Revises: 20260418_0002
Create Date: 2026-04-18 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260418_0003"
down_revision = "20260418_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "data_source_sync_jobs",
        "started_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "data_source_sync_jobs",
        "completed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "data_source_sync_jobs",
        "started_at",
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "data_source_sync_jobs",
        "completed_at",
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )
