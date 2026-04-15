"""Add agent_computes table for remote compute assignment.

Revision ID: 20260414_0001
Revises: 20260413_1738_ff563bc33375
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "20260414_0001"
down_revision = "ff563bc33375"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_computes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Tenant isolation
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        # Agent FK (1:1)
        sa.Column(
            "agent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Compute type and status
        sa.Column("compute_type", sa.String(50), nullable=False, server_default="local"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        # Remote SSH settings
        sa.Column("remote_host", sa.Text, nullable=True),
        sa.Column("remote_port", sa.Integer, nullable=True, server_default="22"),
        sa.Column("remote_user", sa.Text, nullable=True, server_default="root"),
        sa.Column("remote_auth_type", sa.String(50), nullable=True, server_default="key"),
        sa.Column("remote_credentials_encrypted", sa.Text, nullable=True),
        sa.Column(
            "remote_base_path", sa.Text, nullable=True, server_default="/tmp/agent_workspace"
        ),
        # Limits
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column("max_output_chars", sa.Integer, nullable=False, server_default="8000"),
        # Command allowlist override (null = use global default)
        sa.Column("allowed_commands_override", sa.JSON, nullable=True),
        # Connection tracking
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_agent_computes_agent_id", "agent_computes", ["agent_id"])
    op.create_index("ix_agent_computes_tenant_id", "agent_computes", ["tenant_id"])
    op.create_index(
        "ix_agent_computes_status",
        "agent_computes",
        ["compute_type", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_computes_status", table_name="agent_computes")
    op.drop_index("ix_agent_computes_tenant_id", table_name="agent_computes")
    op.drop_index("ix_agent_computes_agent_id", table_name="agent_computes")
    op.drop_table("agent_computes")
