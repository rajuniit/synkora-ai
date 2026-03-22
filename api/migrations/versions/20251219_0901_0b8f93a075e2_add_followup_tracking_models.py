"""Add followup tracking models

Revision ID: 0b8f93a075e2
Revises: 357b02e6ee7e
Create Date: 2025-12-19 09:01:41.322021+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b8f93a075e2'
down_revision = '357b02e6ee7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create followup_configs table
    op.create_table(
        'followup_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('default_followup_frequency_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('default_max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('escalation_targets', sa.JSON(), nullable=True),
        sa.Column('monitoring_keywords', sa.JSON(), nullable=True),
        sa.Column('monitored_channels', sa.JSON(), nullable=True),
        sa.Column('working_hours_only', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('quiet_hours_start', sa.String(5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(5), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_followup_configs_agent_id', 'followup_configs', ['agent_id'])
    op.create_index('ix_followup_configs_tenant_id', 'followup_configs', ['tenant_id'])

    # Create followup_items table
    op.create_table(
        'followup_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('initial_message', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('assignee', sa.String(255), nullable=True),
        sa.Column('mentioned_users', sa.JSON(), nullable=True),
        sa.Column('mentioned_user_names', sa.JSON(), nullable=True),
        sa.Column('channel_id', sa.String(255), nullable=True),
        sa.Column('channel_name', sa.String(255), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('followup_frequency_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('max_followup_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('current_attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_followup_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_followup_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escalated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_targets', sa.JSON(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('completion_reason', sa.String(500), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_followup_items_agent_id', 'followup_items', ['agent_id'])
    op.create_index('ix_followup_items_tenant_id', 'followup_items', ['tenant_id'])
    op.create_index('ix_followup_items_status', 'followup_items', ['status'])
    op.create_index('ix_followup_items_priority', 'followup_items', ['priority'])
    op.create_index('ix_followup_items_assignee', 'followup_items', ['assignee'])
    op.create_index('ix_followup_items_next_followup_at', 'followup_items', ['next_followup_at'])
    op.create_index('ix_followup_items_source_type_id', 'followup_items', ['source_type', 'source_id'])

    # Create followup_history table
    op.create_table(
        'followup_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('followup_item_id', sa.UUID(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('message_sent', sa.Text(), nullable=False),
        sa.Column('message_channel', sa.String(50), nullable=False),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('ai_tone', sa.String(50), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('response_received', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('response_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['followup_item_id'], ['followup_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_followup_history_followup_item_id', 'followup_history', ['followup_item_id'])
    op.create_index('ix_followup_history_attempt_number', 'followup_history', ['followup_item_id', 'attempt_number'])


def downgrade() -> None:
    op.drop_index('ix_followup_history_attempt_number', table_name='followup_history')
    op.drop_index('ix_followup_history_followup_item_id', table_name='followup_history')
    op.drop_table('followup_history')
    
    op.drop_index('ix_followup_items_source_type_id', table_name='followup_items')
    op.drop_index('ix_followup_items_next_followup_at', table_name='followup_items')
    op.drop_index('ix_followup_items_assignee', table_name='followup_items')
    op.drop_index('ix_followup_items_priority', table_name='followup_items')
    op.drop_index('ix_followup_items_status', table_name='followup_items')
    op.drop_index('ix_followup_items_tenant_id', table_name='followup_items')
    op.drop_index('ix_followup_items_agent_id', table_name='followup_items')
    op.drop_table('followup_items')
    
    op.drop_index('ix_followup_configs_tenant_id', table_name='followup_configs')
    op.drop_index('ix_followup_configs_agent_id', table_name='followup_configs')
    op.drop_table('followup_configs')
