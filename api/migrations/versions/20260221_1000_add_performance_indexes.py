"""Add performance indexes for scalability.

This migration adds critical missing indexes that cause table scans:
- messages.conversation_id (called on every message save)
- conversations.agent_id, account_id, app_id (FK lookups)
- agent_sub_agents.parent_agent_id, sub_agent_id (multi-agent operations)
- Partial index on deleted_at for soft delete queries
- Composite index for recent conversations lookup

Revision ID: 20260221_1000
Revises: 20260220_1000_add_widget_key_prefix
Create Date: 2026-02-21

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260221_1000"
down_revision = "add_widget_key_prefix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Critical: Message.conversation_id - O(n) count queries on every message save
    op.create_index(
        "ix_messages_conversation_id",
        "messages",
        ["conversation_id"],
        unique=False,
    )

    # Critical: Message position lookup for ordering
    op.create_index(
        "ix_messages_conversation_position",
        "messages",
        ["conversation_id", "position"],
        unique=False,
    )

    # Conversation foreign key indexes for agent/user/app lookups
    op.create_index(
        "ix_conversations_agent_id",
        "conversations",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_account_id",
        "conversations",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_app_id",
        "conversations",
        ["app_id"],
        unique=False,
    )

    # Composite index for recent conversations by agent (common query pattern)
    op.create_index(
        "ix_conversations_agent_created",
        "conversations",
        ["agent_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # AgentSubAgent junction table indexes for multi-agent operations
    op.create_index(
        "ix_agent_sub_agents_parent_agent_id",
        "agent_sub_agents",
        ["parent_agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_sub_agents_sub_agent_id",
        "agent_sub_agents",
        ["sub_agent_id"],
        unique=False,
    )

    # Composite index for active sub-agents lookup (most common query)
    op.create_index(
        "ix_agent_sub_agents_parent_active",
        "agent_sub_agents",
        ["parent_agent_id", "is_active", "execution_order"],
        unique=False,
    )

    # Partial index for soft delete - only index active records
    # This speeds up WHERE deleted_at IS NULL queries
    # Note: Only conversations table has SoftDeleteMixin with deleted_at column
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_conversations_active
        ON conversations (id)
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    # Remove partial index
    op.execute("DROP INDEX IF EXISTS ix_conversations_active")

    # Remove AgentSubAgent indexes
    op.drop_index("ix_agent_sub_agents_parent_active", table_name="agent_sub_agents")
    op.drop_index("ix_agent_sub_agents_sub_agent_id", table_name="agent_sub_agents")
    op.drop_index("ix_agent_sub_agents_parent_agent_id", table_name="agent_sub_agents")

    # Remove Conversation indexes
    op.drop_index("ix_conversations_agent_created", table_name="conversations")
    op.drop_index("ix_conversations_app_id", table_name="conversations")
    op.drop_index("ix_conversations_account_id", table_name="conversations")
    op.drop_index("ix_conversations_agent_id", table_name="conversations")

    # Remove Message indexes
    op.drop_index("ix_messages_conversation_position", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
