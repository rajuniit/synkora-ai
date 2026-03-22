"""Add Telegram integration tables

Revision ID: add_telegram_integration
Revises:
Create Date: 2026-02-07 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_telegram_integration'
down_revision = 'add_tenant_domain_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create telegram_bots table
    op.create_table(
        'telegram_bots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Bot Configuration
        sa.Column('bot_name', sa.String(255), nullable=False, comment='Display name for the bot'),
        sa.Column('bot_username', sa.String(255), nullable=True, comment='@username without @ (auto-detected)'),
        sa.Column('bot_token', sa.Text(), nullable=False, comment='Encrypted bot token from BotFather'),
        sa.Column('telegram_bot_id', sa.BigInteger(), nullable=True, comment="Telegram's numeric bot ID (auto-detected)"),

        # Webhook Configuration
        sa.Column('use_webhook', sa.Boolean(), nullable=False, server_default='false', comment='Use webhook instead of long polling'),
        sa.Column('webhook_url', sa.Text(), nullable=True, comment='Webhook URL if use_webhook is true'),
        sa.Column('webhook_secret', sa.Text(), nullable=True, comment='Encrypted webhook secret for validation'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('connection_status', sa.String(50), nullable=False, server_default='disconnected', comment='connected, disconnected, error'),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Last error message if any'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )

    # Create indexes for telegram_bots
    op.create_index('ix_telegram_bots_agent_id', 'telegram_bots', ['agent_id'])
    op.create_index('ix_telegram_bots_tenant_id', 'telegram_bots', ['tenant_id'])
    op.create_index('ix_telegram_bots_telegram_bot_id', 'telegram_bots', ['telegram_bot_id'])

    # Create telegram_conversations table
    op.create_table(
        'telegram_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('telegram_bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Telegram Chat Information
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False, comment='Telegram chat ID'),
        sa.Column('telegram_chat_type', sa.String(50), nullable=False, comment='private, group, supergroup, channel'),
        sa.Column('telegram_chat_title', sa.String(255), nullable=True, comment='Chat title for groups/channels'),

        # Telegram User Information
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False, comment='Telegram user ID who initiated'),
        sa.Column('telegram_user_name', sa.String(255), nullable=True, comment='Username without @'),
        sa.Column('telegram_user_display', sa.String(255), nullable=True, comment='Display name (first + last)'),

        # Message tracking
        sa.Column('last_bot_message_id', sa.BigInteger(), nullable=True, comment='Last message ID sent by bot'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['telegram_bot_id'], ['telegram_bots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),

        comment='Mapping between Telegram chats and agent conversations'
    )

    # Create indexes for telegram_conversations
    op.create_index('ix_telegram_conversations_telegram_bot_id', 'telegram_conversations', ['telegram_bot_id'])
    op.create_index('ix_telegram_conversations_conversation_id', 'telegram_conversations', ['conversation_id'])
    op.create_index('ix_telegram_conversations_chat_id', 'telegram_conversations', ['telegram_chat_id'])
    op.create_index('ix_telegram_conversations_user_id', 'telegram_conversations', ['telegram_user_id'])

    # Create unique constraint for bot + chat + user combination
    op.create_index(
        'uq_telegram_conv_bot_chat_user',
        'telegram_conversations',
        ['telegram_bot_id', 'telegram_chat_id', 'telegram_user_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('uq_telegram_conv_bot_chat_user', table_name='telegram_conversations')
    op.drop_index('ix_telegram_conversations_user_id', table_name='telegram_conversations')
    op.drop_index('ix_telegram_conversations_chat_id', table_name='telegram_conversations')
    op.drop_index('ix_telegram_conversations_conversation_id', table_name='telegram_conversations')
    op.drop_index('ix_telegram_conversations_telegram_bot_id', table_name='telegram_conversations')

    op.drop_index('ix_telegram_bots_telegram_bot_id', table_name='telegram_bots')
    op.drop_index('ix_telegram_bots_tenant_id', table_name='telegram_bots')
    op.drop_index('ix_telegram_bots_agent_id', table_name='telegram_bots')

    # Drop tables
    op.drop_table('telegram_conversations')
    op.drop_table('telegram_bots')
