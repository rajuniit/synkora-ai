"""Add max_api_keys column to subscription_plans.

Revision ID: add_max_api_keys_to_plans
Revises: add_slack_event_mode
Create Date: 2026-02-19 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_max_api_keys_to_plans"
down_revision: str | None = "add_slack_event_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add max_api_keys column to subscription_plans table
    op.add_column(
        "subscription_plans",
        sa.Column(
            "max_api_keys",
            sa.Integer(),
            nullable=True,
            comment="Maximum number of API keys (null = unlimited)",
        ),
    )


def downgrade() -> None:
    op.drop_column("subscription_plans", "max_api_keys")
