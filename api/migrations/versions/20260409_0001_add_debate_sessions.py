"""add debate_sessions table for AI War Room

Revision ID: 20260409_0001
Revises: 20260408_0001
Create Date: 2026-04-09

Creates the debate_sessions table that stores multi-agent debate configurations,
participants, messages, and verdicts for the AI War Room feature.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "20260409_0001"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "debate_sessions"):
        op.create_table(
            "debate_sessions",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("topic", sa.Text, nullable=False),
            sa.Column("debate_type", sa.String(50), nullable=False, server_default="structured"),
            sa.Column("rounds", sa.Integer, nullable=False, server_default="3"),
            sa.Column("current_round", sa.Integer, nullable=False, server_default="0"),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("allow_external", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("share_token", sa.String(64), nullable=True, unique=True, index=True),
            sa.Column("participants", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("messages", pg.JSON, nullable=False, server_default="[]"),
            sa.Column("synthesizer_agent_id", pg.UUID(as_uuid=True), nullable=True),
            sa.Column("verdict", sa.Text, nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", pg.UUID(as_uuid=True), nullable=True),
            sa.Column("debate_metadata", pg.JSON, nullable=True, server_default="{}"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                onupdate=sa.func.now(),
            ),
        )

        # Composite index for tenant + status queries
        op.create_index(
            "ix_debate_sessions_tenant_status",
            "debate_sessions",
            ["tenant_id", "status"],
        )


def downgrade() -> None:
    op.drop_index("ix_debate_sessions_tenant_status", table_name="debate_sessions")
    op.drop_table("debate_sessions")
