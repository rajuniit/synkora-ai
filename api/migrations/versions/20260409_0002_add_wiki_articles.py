"""add wiki_articles and wiki_compilation_jobs tables for Knowledge Autopilot

Revision ID: 20260409_0002
Revises: 20260409_0001
Create Date: 2026-04-09

Creates tables for the Knowledge Autopilot wiki system.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20260409_0002"
down_revision = "20260409_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "wiki_articles"):
        op.create_table(
            "wiki_articles",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("knowledge_base_id", sa.Integer, nullable=False, index=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("slug", sa.String(500), nullable=False, index=True),
            sa.Column("content", sa.Text, nullable=False, server_default=""),
            sa.Column("category", sa.String(100), nullable=False, server_default="general"),
            sa.Column("summary", sa.Text, nullable=True),
            sa.Column("source_documents", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("backlinks", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("forward_links", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("auto_generated", sa.Boolean, nullable=False, server_default=sa.text("true")),
            sa.Column("last_compiled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("staleness_score", sa.Float, nullable=False, server_default="0.0"),
            sa.Column("status", sa.String(50), nullable=False, server_default="published"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        )

        op.create_index(
            "ix_wiki_articles_kb_slug",
            "wiki_articles",
            ["knowledge_base_id", "slug"],
            unique=True,
        )
        op.create_index(
            "ix_wiki_articles_kb_category",
            "wiki_articles",
            ["knowledge_base_id", "category"],
        )

    if not bind.dialect.has_table(bind, "wiki_compilation_jobs"):
        op.create_table(
            "wiki_compilation_jobs",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("knowledge_base_id", sa.Integer, nullable=False, index=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="running"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("articles_created", sa.Integer, nullable=False, server_default="0"),
            sa.Column("articles_updated", sa.Integer, nullable=False, server_default="0"),
            sa.Column("errors", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("compilation_metadata", pg.JSON, nullable=True, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_index("ix_wiki_articles_kb_category", table_name="wiki_articles")
    op.drop_index("ix_wiki_articles_kb_slug", table_name="wiki_articles")
    op.drop_table("wiki_articles")
    op.drop_table("wiki_compilation_jobs")
