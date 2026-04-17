"""Add slack_bot_id to agent_output_configs

Revision ID: 20260417_0001
Revises: 20260412_0001
Create Date: 2026-04-17

Changes:
- agent_output_configs: add slack_bot_id UUID FK -> slack_bots.id (nullable, SET NULL on delete)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20260417_0001"
down_revision = "20260412_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_output_configs",
        sa.Column(
            "slack_bot_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("slack_bots.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.create_index(
        "ix_agent_output_configs_slack_bot_id",
        "agent_output_configs",
        ["slack_bot_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_output_configs_slack_bot_id", table_name="agent_output_configs")
    op.drop_column("agent_output_configs", "slack_bot_id")
