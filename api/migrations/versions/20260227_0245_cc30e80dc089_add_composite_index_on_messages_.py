"""add composite index on messages conversation_id position

Revision ID: cc30e80dc089
Revises: 20260223_1000
Create Date: 2026-02-27 02:45:20.671207+00:00

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "cc30e80dc089"
down_revision = "20260223_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for efficient message retrieval by conversation ordered by position
    # Covers: SELECT * FROM messages WHERE conversation_id = ? ORDER BY position
    op.create_index(
        "ix_messages_conversation_position",
        "messages",
        ["conversation_id", "position"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_position", table_name="messages")
