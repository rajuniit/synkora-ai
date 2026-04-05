"""Add missing indexes on telegram_bots, telegram_conversations, and role_permissions.

Without these indexes every query scoped by tenant/agent performs a full table
scan.  At 10 k+ rows that adds 10-50 ms per query.

- telegram_bots.agent_id      — bot lookup by agent
- telegram_bots.tenant_id     — tenant-scoped queries
- telegram_conversations.telegram_bot_id — conversation lookup by bot
- telegram_conversations.conversation_id — join from conversations table
- role_permissions.permission_id          — permission check by permission

Revision ID: 20260405_0001
Revises: 20260404_0001
Create Date: 2026-04-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260405_0001"
down_revision: str | None = "20260404_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_telegram_bots_agent_id", "telegram_bots", ["agent_id"], unique=False, if_not_exists=True)
    op.create_index("ix_telegram_bots_tenant_id", "telegram_bots", ["tenant_id"], unique=False, if_not_exists=True)
    op.create_index(
        "ix_telegram_conversations_telegram_bot_id",
        "telegram_conversations",
        ["telegram_bot_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_telegram_conversations_conversation_id",
        "telegram_conversations",
        ["conversation_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_telegram_conversations_conversation_id", table_name="telegram_conversations")
    op.drop_index("ix_telegram_conversations_telegram_bot_id", table_name="telegram_conversations")
    op.drop_index("ix_telegram_bots_tenant_id", table_name="telegram_bots")
    op.drop_index("ix_telegram_bots_agent_id", table_name="telegram_bots")
