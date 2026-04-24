"""add agent_a2a_tasks table for A2A protocol task tracking

Revision ID: 20260423_0001
Revises: 20260418_0002
Create Date: 2026-04-23

Creates the agent_a2a_tasks table that persists asynchronous A2A protocol tasks
for agent-to-agent communication following the Google A2A specification.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260423_0001"
down_revision = "20260418_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "agent_a2a_tasks"):
        op.create_table(
            "agent_a2a_tasks",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("agent_id", UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("task_id", sa.String(255), nullable=False, unique=True),
            sa.Column("context_id", sa.String(255), nullable=False),
            sa.Column("status", sa.String(50), nullable=False, server_default="submitted"),
            sa.Column("input_message", JSONB, nullable=False, server_default="{}"),
            sa.Column("output_text", sa.Text, nullable=True),
            sa.Column("error_code", sa.String(100), nullable=True),
            sa.Column("error_message", sa.String(2000), nullable=True),
            sa.Column("caller_info", JSONB, nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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

        op.create_index("ix_a2a_task_task_id", "agent_a2a_tasks", ["task_id"], unique=True)
        op.create_index("ix_a2a_task_agent_status", "agent_a2a_tasks", ["agent_id", "status"])
        op.create_index("ix_a2a_task_tenant_status", "agent_a2a_tasks", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_a2a_task_tenant_status", table_name="agent_a2a_tasks")
    op.drop_index("ix_a2a_task_agent_status", table_name="agent_a2a_tasks")
    op.drop_index("ix_a2a_task_task_id", table_name="agent_a2a_tasks")
    op.drop_table("agent_a2a_tasks")
