"""add conversation memory fields

Revision ID: add_conversation_memory_fields
Revises: add_user_oauth_tokens
Create Date: 2026-02-04 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_conversation_memory_fields'
down_revision = 'add_user_oauth_tokens'
branch_labels = None
depends_on = None


def upgrade():
    # Add memory/context management fields to conversations table
    op.add_column(
        'conversations',
        sa.Column(
            'context_summary',
            sa.Text(),
            nullable=True,
            comment='LLM-generated summary of conversation for context continuity'
        )
    )
    op.add_column(
        'conversations',
        sa.Column(
            'summary_updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When the context summary was last updated'
        )
    )
    op.add_column(
        'conversations',
        sa.Column(
            'summary_message_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Message count when summary was generated (for incremental updates)'
        )
    )
    op.add_column(
        'conversations',
        sa.Column(
            'total_tokens_estimated',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Estimated total tokens in conversation history'
        )
    )


def downgrade():
    op.drop_column('conversations', 'total_tokens_estimated')
    op.drop_column('conversations', 'summary_message_count')
    op.drop_column('conversations', 'summary_updated_at')
    op.drop_column('conversations', 'context_summary')
