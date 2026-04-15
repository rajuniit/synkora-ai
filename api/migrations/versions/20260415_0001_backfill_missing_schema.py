"""backfill missing schema from skipped branch migrations

Revision ID: 20260415_0001
Revises: 4f6f10bce079
Create Date: 2026-04-15

Applies schema changes from the 20260413_0002 company-brain migration that
were never executed against this database because the alembic version was
already ahead of the merge-point when those branch migrations were added.

Missing items:
  - data_source_documents.storage_tier (VARCHAR 20, NOT NULL, default 'hot')
  - data_source_documents.search_vector (tsvector GENERATED column)
  - DataSourceType enum values: JIRA, CLICKUP, LINEAR, NOTION, CONFLUENCE, ASANA
  - external_org_id column on conversations (external_user_id already exists)
"""

import sqlalchemy as sa
from alembic import op

revision = "20260415_0001"
down_revision = "4f6f10bce079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. data_source_documents.storage_tier
    # ------------------------------------------------------------------
    existing = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='data_source_documents' AND column_name='storage_tier'"
        )
    ).fetchone()
    if not existing:
        op.add_column(
            "data_source_documents",
            sa.Column("storage_tier", sa.String(20), nullable=False, server_default="hot"),
        )
        op.execute(
            "ALTER TABLE data_source_documents "
            "ADD CONSTRAINT ck_dsd_storage_tier "
            "CHECK (storage_tier IN ('hot', 'warm', 'archive'))"
        )
        op.create_index(
            "ix_dsd_tenant_tier_created",
            "data_source_documents",
            ["tenant_id", "storage_tier", "source_created_at"],
        )

    # ------------------------------------------------------------------
    # 2. data_source_documents.search_vector (generated tsvector)
    # ------------------------------------------------------------------
    sv_exists = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='data_source_documents' AND column_name='search_vector'"
        )
    ).fetchone()
    if not sv_exists:
        op.execute(
            """
            ALTER TABLE data_source_documents
            ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('english',
                    coalesce(title, '') || ' ' || coalesce(content, ''))
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_dsd_search_vector "
            "ON data_source_documents USING gin(search_vector)"
        )

    # ------------------------------------------------------------------
    # 3. Extend DataSourceType enum
    # ------------------------------------------------------------------
    for value in ["JIRA", "CLICKUP", "LINEAR", "NOTION", "CONFLUENCE", "ASANA"]:
        op.execute(f"ALTER TYPE datasourcetype ADD VALUE IF NOT EXISTS '{value}'")

    # ------------------------------------------------------------------
    # 4. conversations.external_org_id (external_user_id already exists)
    # ------------------------------------------------------------------
    org_exists = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='conversations' AND column_name='external_org_id'"
        )
    ).fetchone()
    if not org_exists:
        op.add_column(
            "conversations",
            sa.Column("external_org_id", sa.String(255), nullable=True),
        )
        op.create_index(
            "ix_conversations_external_org_id",
            "conversations",
            ["external_org_id"],
        )


def downgrade() -> None:
    # This migration is a one-way backfill for a production database that missed
    # branch migrations 20260412_0001 and 20260413_0002. Those migrations are always
    # present in the chain and own every object this migration conditionally adds.
    # Their own downgrades handle cleanup — nothing to undo here.
    pass
