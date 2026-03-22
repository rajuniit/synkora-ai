"""Add Slack Event Mode fields.

Revision ID: add_slack_event_mode
Revises: add_paddle_payment_fields
Create Date: 2026-02-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_slack_event_mode"
down_revision: str | None = "add_paddle_payment_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add connection_mode column with default "socket" for backwards compatibility
    op.add_column(
        "slack_bots",
        sa.Column(
            "connection_mode",
            sa.String(20),
            nullable=False,
            server_default="socket",
            comment="Connection mode: socket or event",
        ),
    )

    # Add signing_secret column for Event Mode verification (encrypted)
    op.add_column(
        "slack_bots",
        sa.Column(
            "signing_secret",
            sa.Text(),
            nullable=True,
            comment="Encrypted signing secret for Event Mode",
        ),
    )

    # Add webhook_url column for Event Mode (auto-generated)
    op.add_column(
        "slack_bots",
        sa.Column(
            "webhook_url",
            sa.Text(),
            nullable=True,
            comment="Auto-generated webhook URL for Event Mode",
        ),
    )

    # Make slack_app_token nullable (not needed for Event Mode)
    op.alter_column(
        "slack_bots",
        "slack_app_token",
        existing_type=sa.Text(),
        nullable=True,
        comment="Encrypted app-level token for Socket Mode (xapp-*)",
    )


def downgrade() -> None:
    # Remove webhook_url column
    op.drop_column("slack_bots", "webhook_url")

    # Remove signing_secret column
    op.drop_column("slack_bots", "signing_secret")

    # Remove connection_mode column
    op.drop_column("slack_bots", "connection_mode")

    # Revert slack_app_token to non-nullable
    # Note: This may fail if there are null values - run cleanup before downgrade
    op.alter_column(
        "slack_bots",
        "slack_app_token",
        existing_type=sa.Text(),
        nullable=False,
        comment="Encrypted app-level token for Socket Mode (xapp-*)",
    )
