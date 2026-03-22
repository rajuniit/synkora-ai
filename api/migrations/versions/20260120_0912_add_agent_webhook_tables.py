"""add_agent_webhook_tables

Revision ID: a1b2c3d4e5f6
Revises: 907da4603212
Create Date: 2026-01-20 09:12:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '907da4603212'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agent_webhooks table
    op.create_table(
        'agent_webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('webhook_url', sa.String(length=512), nullable=False),
        sa.Column('secret', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('event_types', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_webhooks_agent_id', 'agent_webhooks', ['agent_id'])
    op.create_index('idx_agent_webhooks_provider', 'agent_webhooks', ['provider'])
    op.create_index('idx_agent_webhooks_webhook_url', 'agent_webhooks', ['webhook_url'], unique=True)
    op.create_index('idx_agent_webhooks_is_active', 'agent_webhooks', ['is_active'])

    # Create agent_webhook_events table
    op.create_table(
        'agent_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('parsed_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agent_execution_id', sa.String(length=255), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['agent_webhooks.id'], ondelete='CASCADE', name='fk_webhook_events_webhook_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_events_webhook_id', 'agent_webhook_events', ['webhook_id'])
    op.create_index('idx_webhook_events_event_id', 'agent_webhook_events', ['event_id'])
    op.create_index('idx_webhook_events_status', 'agent_webhook_events', ['status'])
    op.create_index('idx_webhook_events_created_at', 'agent_webhook_events', ['created_at'])
    op.create_index('idx_webhook_events_agent_execution_id', 'agent_webhook_events', ['agent_execution_id'])


def downgrade() -> None:
    # Drop agent_webhook_events table
    op.drop_index('idx_webhook_events_agent_execution_id', table_name='agent_webhook_events')
    op.drop_index('idx_webhook_events_created_at', table_name='agent_webhook_events')
    op.drop_index('idx_webhook_events_status', table_name='agent_webhook_events')
    op.drop_index('idx_webhook_events_event_id', table_name='agent_webhook_events')
    op.drop_index('idx_webhook_events_webhook_id', table_name='agent_webhook_events')
    op.drop_table('agent_webhook_events')

    # Drop agent_webhooks table
    op.drop_index('idx_agent_webhooks_is_active', table_name='agent_webhooks')
    op.drop_index('idx_agent_webhooks_webhook_url', table_name='agent_webhooks')
    op.drop_index('idx_agent_webhooks_provider', table_name='agent_webhooks')
    op.drop_index('idx_agent_webhooks_agent_id', table_name='agent_webhooks')
    op.drop_table('agent_webhooks')
