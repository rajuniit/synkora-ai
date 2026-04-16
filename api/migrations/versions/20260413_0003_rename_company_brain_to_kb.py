"""rename company_brain tables to kb_brain scoped by knowledge_base_id

Revision ID: 20260413_0003
Revises: 20260413_0002
Create Date: 2026-04-13

Drops the company_brain_* tables (which were a parallel concept) and
replaces them with kb_* tables scoped to knowledge_base_id, making
the Brain feature a first-class extension of the existing KnowledgeBase.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260413_0003"
down_revision = "20260413_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Drop old company_brain_* tables (order: relationships → cursors → entities)
    # Use IF EXISTS so re-runs don't fail if they were already dropped.
    # ------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS company_brain_relationships")
    op.execute("DROP TABLE IF EXISTS company_brain_cursors")
    op.execute("DROP TABLE IF EXISTS company_brain_entities")

    # ------------------------------------------------------------------
    # kb_sync_cursors — incremental sync cursor per (knowledge_base, data_source)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS kb_sync_cursors (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            data_source_id INTEGER NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
            cursor_type VARCHAR(50) NOT NULL,
            cursor_value TEXT NOT NULL,
            docs_seen INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_kb_cursor_source_type UNIQUE (data_source_id, cursor_type)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_sync_cursors_tenant_id ON kb_sync_cursors(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_sync_cursors_knowledge_base_id ON kb_sync_cursors(knowledge_base_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_sync_cursors_data_source_id ON kb_sync_cursors(data_source_id)")

    # ------------------------------------------------------------------
    # kb_entities — canonical cross-source entities scoped to a KB
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS kb_entities (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            entity_type VARCHAR(50) NOT NULL,
            canonical_name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            identifiers JSON NOT NULL DEFAULT '{}',
            display_names JSON NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_kb_entity_kb_email UNIQUE (knowledge_base_id, email)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_entities_tenant_id ON kb_entities(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_entities_knowledge_base_id ON kb_entities(knowledge_base_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_entities_entity_type ON kb_entities(entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_entities_email ON kb_entities(email)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_entity_identifiers "
        "ON kb_entities USING gin((identifiers::jsonb))"
    )

    # ------------------------------------------------------------------
    # kb_relationships — typed edges in the knowledge graph
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS kb_relationships (
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            source_entity_id INTEGER REFERENCES kb_entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER REFERENCES kb_entities(id) ON DELETE CASCADE,
            source_doc_id INTEGER REFERENCES data_source_documents(id) ON DELETE SET NULL,
            relation_type VARCHAR(100) NOT NULL,
            rel_metadata JSON NOT NULL DEFAULT '{}',
            occurred_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_tenant_id ON kb_relationships(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_knowledge_base_id ON kb_relationships(knowledge_base_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_source_entity_id ON kb_relationships(source_entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_target_entity_id ON kb_relationships(target_entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_source_doc_id ON kb_relationships(source_doc_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_relationships_relation_type ON kb_relationships(relation_type)")


def downgrade() -> None:
    op.drop_table("kb_relationships")
    op.execute("DROP INDEX IF EXISTS ix_kb_entity_identifiers")
    op.drop_table("kb_entities")
    op.drop_table("kb_sync_cursors")

    # Recreate the old company_brain_* tables (minimal schema for rollback)
    op.create_table(
        "company_brain_entities",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("identifiers", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("display_names", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "company_brain_cursors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_source_id", sa.Integer, sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cursor_type", sa.String(50), nullable=False),
        sa.Column("cursor_value", sa.Text, nullable=False),
        sa.Column("docs_seen", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "company_brain_relationships",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_entity_id", sa.Integer, sa.ForeignKey("company_brain_entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("target_entity_id", sa.Integer, sa.ForeignKey("company_brain_entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_doc_id", sa.Integer, sa.ForeignKey("data_source_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relation_type", sa.String(100), nullable=False),
        sa.Column("rel_metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
