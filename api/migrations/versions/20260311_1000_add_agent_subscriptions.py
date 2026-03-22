"""add_agent_subscriptions

Revision ID: add_agent_subscriptions
Revises: 41f25b970c7a
Create Date: 2026-03-11 10:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_agent_subscriptions"
down_revision = "41f25b970c7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add allow_subscriptions column to agents table
    op.add_column(
        "agents",
        sa.Column("allow_subscriptions", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create agent_subscriptions table
    op.create_table(
        "agent_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("unsubscribe_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "email", name="uq_agent_subscription_agent_email"),
        sa.UniqueConstraint("unsubscribe_token", name="uq_agent_subscription_token"),
    )
    op.create_index("idx_agent_subscriptions_agent_id", "agent_subscriptions", ["agent_id"])
    op.create_index("idx_agent_subscriptions_is_active", "agent_subscriptions", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_agent_subscriptions_is_active", table_name="agent_subscriptions")
    op.drop_index("idx_agent_subscriptions_agent_id", table_name="agent_subscriptions")
    op.drop_table("agent_subscriptions")
    op.drop_column("agents", "allow_subscriptions")
