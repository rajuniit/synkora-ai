"""add daily_digests table for pre-computed data source summaries

Revision ID: 20260418_0002
Revises: 20260418_0001
Create Date: 2026-04-18 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260418_0002"
down_revision = "20260418_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_digests",
        sa.Column("id", UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "data_source_id",
            sa.Integer,
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("digest_date", sa.Date, nullable=False),
        sa.Column("structured_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("summary_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("items_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("data_source_id", "digest_date", name="uq_daily_digest_source_date"),
        if_not_exists=True,
    )

    op.create_index("ix_daily_digests_data_source_id", "daily_digests", ["data_source_id"], if_not_exists=True)
    op.create_index("ix_daily_digests_tenant_date", "daily_digests", ["tenant_id", "digest_date"], if_not_exists=True)
    op.create_index("ix_daily_digests_status", "daily_digests", ["status"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_daily_digests_status", table_name="daily_digests")
    op.drop_index("ix_daily_digests_tenant_date", table_name="daily_digests")
    op.drop_index("ix_daily_digests_data_source_id", table_name="daily_digests")
    op.drop_table("daily_digests")
