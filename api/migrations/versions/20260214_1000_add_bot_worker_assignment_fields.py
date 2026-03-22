"""Add worker assignment fields to bot tables for scalable worker pool.

Revision ID: f8e7d6c5b4a3
Revises: cdeeb66d1a12
Create Date: 2026-02-14 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8e7d6c5b4a3"
down_revision: str | None = "cdeeb66d1a12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add worker assignment columns to slack_bots
    op.add_column(
        "slack_bots",
        sa.Column(
            "assigned_worker_id",
            sa.String(255),
            nullable=True,
            comment="ID of the worker managing this bot",
        ),
    )
    op.add_column(
        "slack_bots",
        sa.Column(
            "worker_connected_at",
            sa.DateTime(),
            nullable=True,
            comment="When the worker established the connection",
        ),
    )

    # Add worker assignment columns to telegram_bots
    op.add_column(
        "telegram_bots",
        sa.Column(
            "assigned_worker_id",
            sa.String(255),
            nullable=True,
            comment="ID of the worker managing this bot",
        ),
    )
    op.add_column(
        "telegram_bots",
        sa.Column(
            "worker_connected_at",
            sa.DateTime(),
            nullable=True,
            comment="When the worker established the connection",
        ),
    )

    # Create index for efficient lookups by worker
    op.create_index(
        "ix_slack_bots_assigned_worker_id",
        "slack_bots",
        ["assigned_worker_id"],
        unique=False,
    )
    op.create_index(
        "ix_telegram_bots_assigned_worker_id",
        "telegram_bots",
        ["assigned_worker_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_telegram_bots_assigned_worker_id", table_name="telegram_bots")
    op.drop_index("ix_slack_bots_assigned_worker_id", table_name="slack_bots")

    # Drop columns from telegram_bots
    op.drop_column("telegram_bots", "worker_connected_at")
    op.drop_column("telegram_bots", "assigned_worker_id")

    # Drop columns from slack_bots
    op.drop_column("slack_bots", "worker_connected_at")
    op.drop_column("slack_bots", "assigned_worker_id")
