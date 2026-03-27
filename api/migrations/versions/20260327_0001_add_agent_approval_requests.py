"""add agent_approval_requests table for HITL flows

Revision ID: 20260327_0001
Revises: 20260326_0001
Create Date: 2026-03-27

Creates the agent_approval_requests table that persists pending human-in-the-loop
approval gates for autonomous agent tool calls.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = "20260327_0001"
down_revision = "20260326_0001"
branch_labels = None
depends_on = None

# Define the enum once; create_type=False means create_table won't try to
# create it automatically — we handle creation explicitly with checkfirst=True.
approval_status_enum = ENUM(
    "pending", "approved", "rejected", "expired", "executed",
    name="approval_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Creates the type only if it doesn't already exist (idempotent).
    approval_status_enum.create(bind, checkfirst=True)

    # Skip table creation if it already exists (e.g. from a previously
    # interrupted migration run that was never stamped).
    if not bind.dialect.has_table(bind, "agent_approval_requests"):
        op.create_table(
            "agent_approval_requests",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "task_id",
                pg.UUID(as_uuid=True),
                sa.ForeignKey("scheduled_tasks.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_id", pg.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_name", sa.String(255), nullable=False),
            sa.Column("tool_name", sa.String(255), nullable=False),
            sa.Column("tool_args", pg.JSONB, nullable=False, server_default="{}"),
            sa.Column("tool_args_hash", sa.String(64), nullable=False),
            sa.Column(
                "status",
                approval_status_enum,
                nullable=False,
                server_default="pending",
            ),
            sa.Column("notification_channel", sa.String(50), nullable=False),
            sa.Column("notification_ref", pg.JSONB, nullable=False, server_default="{}"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("execution_result", pg.JSONB, nullable=True),
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

        op.create_index("ix_approval_task_status", "agent_approval_requests", ["task_id", "status"])
        op.create_index("ix_approval_tenant_status", "agent_approval_requests", ["tenant_id", "status"])
        op.create_index("ix_approval_agent_status", "agent_approval_requests", ["agent_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_approval_agent_status", table_name="agent_approval_requests")
    op.drop_index("ix_approval_tenant_status", table_name="agent_approval_requests")
    op.drop_index("ix_approval_task_status", table_name="agent_approval_requests")
    op.drop_table("agent_approval_requests")
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
