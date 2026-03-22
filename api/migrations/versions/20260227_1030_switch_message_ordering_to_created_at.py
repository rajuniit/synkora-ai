"""switch message ordering from position to created_at

Revision ID: 20260227_1030
Revises: cc30e80dc089
Create Date: 2026-02-27 10:30:00.000000+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_1030"
down_revision = "cc30e80dc089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old position-based index
    op.drop_index("ix_messages_conversation_position", table_name="messages", if_exists=True)

    # Create new composite index for message retrieval by conversation ordered by created_at
    # Covers: SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at
    op.create_index(
        "ix_messages_conversation_created_at",
        "messages",
        ["conversation_id", "created_at"],
        if_not_exists=True,
    )

    # Make position column nullable (no longer required since we use created_at for ordering)
    op.alter_column(
        "messages",
        "position",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Restore position as non-nullable (with default 0 for existing rows)
    op.execute("UPDATE messages SET position = 0 WHERE position IS NULL")
    op.alter_column(
        "messages",
        "position",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Drop the created_at index
    op.drop_index("ix_messages_conversation_created_at", table_name="messages", if_exists=True)

    # Restore the position-based index
    op.create_index(
        "ix_messages_conversation_position",
        "messages",
        ["conversation_id", "position"],
    )
