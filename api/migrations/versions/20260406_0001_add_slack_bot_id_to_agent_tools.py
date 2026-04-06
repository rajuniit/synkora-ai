"""Add slack_bot_id to agent_tools for explicit Slack bot selection.

Adds a nullable FK from agent_tools.slack_bot_id → slack_bots.id so that
a Slack tool can be pinned to a specific bot rather than relying on the
auto-discovery fallback.

Revision ID: 20260406_0001
Revises: 20260405_0001
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_0001"
down_revision: str | None = "20260405_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_tools",
        sa.Column(
            "slack_bot_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Optional: specific Slack bot to use for this tool",
        ),
    )
    op.create_foreign_key(
        "fk_agent_tools_slack_bot_id",
        "agent_tools",
        "slack_bots",
        ["slack_bot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_agent_tools_slack_bot_id", "agent_tools", ["slack_bot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_tools_slack_bot_id", table_name="agent_tools")
    op.drop_constraint("fk_agent_tools_slack_bot_id", "agent_tools", type_="foreignkey")
    op.drop_column("agent_tools", "slack_bot_id")
