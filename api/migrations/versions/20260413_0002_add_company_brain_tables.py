"""add company brain tables

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13

Adds:
  - company_brain_cursors       — per-source sync cursor state
  - company_brain_entities      — canonical cross-source entities
  - company_brain_relationships — knowledge-graph edges
  - data_source_documents.storage_tier column
  - data_source_documents.search_vector tsvector column + GIN index
  - DataSourceType enum values: JIRA, CLICKUP, LINEAR, NOTION, CONFLUENCE, ASANA
"""

import sqlalchemy as sa
from alembic import op

revision = "20260413_0002"
down_revision = "20260413_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extend DataSourceType enum
    # ------------------------------------------------------------------
    new_types = ["JIRA", "CLICKUP", "LINEAR", "NOTION", "CONFLUENCE", "ASANA"]
    for t in new_types:
        op.execute(f"ALTER TYPE datasourcetype ADD VALUE IF NOT EXISTS '{t}'")

    # ------------------------------------------------------------------
    # 2. Add storage_tier + search_vector to data_source_documents
    # ------------------------------------------------------------------
    op.add_column(
        "data_source_documents",
        sa.Column(
            "storage_tier",
            sa.String(20),
            nullable=False,
            server_default="hot",
        ),
    )
    op.create_check_constraint(
        "ck_dsd_storage_tier",
        "data_source_documents",
        "storage_tier IN ('hot', 'warm', 'archive')",
    )
    op.create_index(
        "ix_dsd_tenant_tier_created",
        "data_source_documents",
        ["tenant_id", "storage_tier", "source_created_at"],
    )

    # Add tsvector column for full-text search (PostgresFTS backend)
    op.execute(
        """
        ALTER TABLE data_source_documents
        ADD COLUMN IF NOT EXISTS search_vector tsvector
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
    # 3. company_brain_cursors
    # ------------------------------------------------------------------
    op.create_table(
        "company_brain_cursors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_source_id",
            sa.Integer,
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("cursor_type", sa.String(50), nullable=False),
        sa.Column("cursor_value", sa.Text, nullable=False),
        sa.Column("docs_seen", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.UniqueConstraint("data_source_id", "cursor_type", name="uq_cb_cursor_source_type"),
    )

    # ------------------------------------------------------------------
    # 4. company_brain_entities
    # ------------------------------------------------------------------
    op.create_table(
        "company_brain_entities",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("identifiers", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("display_names", sa.JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "email", name="uq_cb_entity_tenant_email"),
    )
    # GIN index for identifier lookups (cast json→jsonb since plain json has no GIN operator class)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cb_entity_identifiers "
        "ON company_brain_entities USING gin((identifiers::jsonb))"
    )

    # ------------------------------------------------------------------
    # 5. company_brain_relationships
    # ------------------------------------------------------------------
    op.create_table(
        "company_brain_relationships",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_entity_id",
            sa.Integer,
            sa.ForeignKey("company_brain_entities.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "target_entity_id",
            sa.Integer,
            sa.ForeignKey("company_brain_entities.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "source_doc_id",
            sa.Integer,
            sa.ForeignKey("data_source_documents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("relation_type", sa.String(100), nullable=False, index=True),
        sa.Column("rel_metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("company_brain_relationships")
    op.drop_table("company_brain_entities")
    op.drop_table("company_brain_cursors")

    op.execute("DROP INDEX IF EXISTS ix_dsd_search_vector")
    op.execute("ALTER TABLE data_source_documents DROP COLUMN IF EXISTS search_vector")
    op.drop_index("ix_dsd_tenant_tier_created", table_name="data_source_documents")
    op.drop_constraint("ck_dsd_storage_tier", "data_source_documents", type_="check")
    op.drop_column("data_source_documents", "storage_tier")

    # Note: Postgres doesn't support removing enum values; new values persist after downgrade.
