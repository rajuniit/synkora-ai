"""fix data_sources datetime columns to timestamp with time zone

Revision ID: 20260418_0004
Revises: 20260418_0003
Create Date: 2026-04-18 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260418_0004"
down_revision = "20260418_0003"
branch_labels = None
depends_on = None

_TZ = sa.DateTime(timezone=True)
_NO_TZ = sa.DateTime(timezone=False)
_USING = "AT TIME ZONE 'UTC'"

_DATA_SOURCES_COLS = ["token_expires_at", "last_sync_at", "next_sync_at"]
_DATA_SOURCE_DOCUMENTS_COLS = ["source_created_at", "source_updated_at"]


def upgrade() -> None:
    for col in _DATA_SOURCES_COLS:
        op.alter_column(
            "data_sources", col,
            type_=_TZ, existing_type=_NO_TZ,
            postgresql_using=f"{col} {_USING}",
        )
    for col in _DATA_SOURCE_DOCUMENTS_COLS:
        op.alter_column(
            "data_source_documents", col,
            type_=_TZ, existing_type=_NO_TZ,
            postgresql_using=f"{col} {_USING}",
        )


def downgrade() -> None:
    for col in _DATA_SOURCES_COLS:
        op.alter_column(
            "data_sources", col,
            type_=_NO_TZ, existing_type=_TZ,
            postgresql_using=f"{col} {_USING}",
        )
    for col in _DATA_SOURCE_DOCUMENTS_COLS:
        op.alter_column(
            "data_source_documents", col,
            type_=_NO_TZ, existing_type=_TZ,
            postgresql_using=f"{col} {_USING}",
        )
