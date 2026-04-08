"""Add created_by to slack_bots, telegram_bots, and whatsapp_bots.

Records which account created each bot so that OAuth tokens (e.g. Twitter)
can be resolved to the correct user when the agent runs from a channel
message rather than a web session.

Revision ID: 20260408_0001
Revises: 20260406_0001
Create Date: 2026-04-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260408_0001"
down_revision: str | None = "20260406_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "slack_bots",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Account that created this bot (used to resolve OAuth tokens)",
        ),
    )
    op.create_foreign_key(
        "fk_slack_bots_created_by",
        "slack_bots",
        "accounts",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "telegram_bots",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Account that created this bot (used to resolve OAuth tokens)",
        ),
    )
    op.create_foreign_key(
        "fk_telegram_bots_created_by",
        "telegram_bots",
        "accounts",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "whatsapp_bots",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Account that created this bot (used to resolve OAuth tokens)",
        ),
    )
    op.create_foreign_key(
        "fk_whatsapp_bots_created_by",
        "whatsapp_bots",
        "accounts",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_whatsapp_bots_created_by", "whatsapp_bots", type_="foreignkey")
    op.drop_column("whatsapp_bots", "created_by")

    op.drop_constraint("fk_telegram_bots_created_by", "telegram_bots", type_="foreignkey")
    op.drop_column("telegram_bots", "created_by")

    op.drop_constraint("fk_slack_bots_created_by", "slack_bots", type_="foreignkey")
    op.drop_column("slack_bots", "created_by")
