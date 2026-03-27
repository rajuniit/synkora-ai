"""add autonomous_enabled to agents

Revision ID: 20260326_0001
Revises: 20260319_0001
Create Date: 2026-03-26

Adds autonomous_enabled boolean column to the agents table so the dashboard
can filter/display agents that have an autonomous schedule configured.
Everything else (goal, schedule, memory conversation ID) lives in
ScheduledTask.config (JSONB) — no further schema change needed.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260326_0001"
down_revision = "20260319_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "autonomous_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether this agent has an active autonomous schedule",
        ),
    )
    op.create_index("ix_agents_autonomous_enabled", "agents", ["autonomous_enabled"])


def downgrade() -> None:
    op.drop_index("ix_agents_autonomous_enabled", table_name="agents")
    op.drop_column("agents", "autonomous_enabled")
