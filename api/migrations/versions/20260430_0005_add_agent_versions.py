"""add agent_versions table for configuration snapshot history

Revision ID: 20260430_0005
Revises: 20260430_0004
Create Date: 2026-04-30

Creates the agent_versions table that stores immutable snapshots of agent
configuration each time an agent is saved, enabling audit history and rollback.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "20260430_0005"
down_revision = "20260430_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Skip table creation if it already exists (idempotent guard).
    if not bind.dialect.has_table(bind, "agent_versions"):
        op.create_table(
            "agent_versions",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "agent_id",
                pg.UUID(as_uuid=True),
                sa.ForeignKey("agents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_by",
                pg.UUID(as_uuid=True),
                sa.ForeignKey("accounts.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("change_description", sa.String(500), nullable=True),
            sa.Column("snapshot", pg.JSONB, nullable=False, server_default="{}"),
            sa.Column("changed_fields", pg.JSONB, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
        )

        # Composite unique index: each agent has exactly one row per version number
        op.create_index(
            "uq_agent_versions_agent_id_version_number",
            "agent_versions",
            ["agent_id", "version_number"],
            unique=True,
        )

        # Supporting indexes
        op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])
        op.create_index("ix_agent_versions_tenant_id", "agent_versions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_versions_tenant_id", table_name="agent_versions")
    op.drop_index("ix_agent_versions_agent_id", table_name="agent_versions")
    op.drop_index("uq_agent_versions_agent_id_version_number", table_name="agent_versions")
    op.drop_table("agent_versions")
