"""Add key_prefix column to agent_widgets table.

Revision ID: add_widget_key_prefix
Revises: add_max_api_keys_to_plans
Create Date: 2026-02-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_widget_key_prefix"
down_revision: str | None = "add_max_api_keys_to_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add key_prefix column to agent_widgets table
    op.add_column(
        "agent_widgets",
        sa.Column(
            "key_prefix",
            sa.String(32),
            nullable=True,
            comment="First 16 chars of API key for identification/lookup",
        ),
    )

    # Add unique index for key_prefix
    op.create_index(
        "ix_agent_widgets_key_prefix",
        "agent_widgets",
        ["key_prefix"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_widgets_key_prefix", table_name="agent_widgets")
    op.drop_column("agent_widgets", "key_prefix")
