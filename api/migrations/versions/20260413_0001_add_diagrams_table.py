"""add diagrams table for diagram generation service

Revision ID: 20260413_0001
Revises: 20260409_0002
Create Date: 2026-04-13

Creates the diagrams table for storing generated technical diagram specs and S3 keys.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20260413_0001"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagrams",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("agent_id", pg.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("conversation_id", pg.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("message_id", pg.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("diagram_type", sa.String(50), nullable=False),
        sa.Column("style", sa.Integer, nullable=True),
        sa.Column("spec", pg.JSON, nullable=False),
        sa.Column("svg_key", sa.String(500), nullable=True),
        sa.Column("png_key", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_diagrams_tenant_id", "diagrams", ["tenant_id"])
    op.create_index("ix_diagrams_conversation_id", "diagrams", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_diagrams_conversation_id")
    op.drop_index("ix_diagrams_tenant_id")
    op.drop_table("diagrams")
