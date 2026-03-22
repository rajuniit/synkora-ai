"""add_agent_output_config_tables

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-01-22 14:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agent_output_configs table
    op.create_table(
        'agent_output_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('oauth_app_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.Enum('slack', 'email', 'webhook', 'ms_teams', 'discord', 
                                     name='outputprovider'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('output_template', sa.Text(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('send_on_webhook_trigger', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('send_on_chat_completion', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retry_on_failure', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['oauth_app_id'], ['oauth_apps.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_output_configs_agent_id', 'agent_output_configs', ['agent_id'])
    op.create_index('idx_output_configs_tenant_id', 'agent_output_configs', ['tenant_id'])
    op.create_index('idx_output_configs_provider', 'agent_output_configs', ['provider'])
    op.create_index('idx_output_configs_is_enabled', 'agent_output_configs', ['is_enabled'])

    # Create agent_output_deliveries table
    op.create_table(
        'agent_output_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('output_config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.Enum('pending', 'sending', 'delivered', 'failed', 'retrying',
                                    name='deliverystatus'), nullable=False, server_default='pending'),
        sa.Column('provider', sa.Enum('slack', 'email', 'webhook', 'ms_teams', 'discord',
                                     name='outputprovider'), nullable=False),
        sa.Column('formatted_output', sa.Text(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('provider_response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('provider_message_id', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['output_config_id'], ['agent_output_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['webhook_event_id'], ['agent_webhook_events.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_output_deliveries_config_id', 'agent_output_deliveries', ['output_config_id'])
    op.create_index('idx_output_deliveries_agent_id', 'agent_output_deliveries', ['agent_id'])
    op.create_index('idx_output_deliveries_tenant_id', 'agent_output_deliveries', ['tenant_id'])
    op.create_index('idx_output_deliveries_webhook_event_id', 'agent_output_deliveries', ['webhook_event_id'])
    op.create_index('idx_output_deliveries_status', 'agent_output_deliveries', ['status'])
    op.create_index('idx_output_deliveries_created_at', 'agent_output_deliveries', ['created_at'])


def downgrade() -> None:
    # Drop agent_output_deliveries table
    op.drop_index('idx_output_deliveries_created_at', table_name='agent_output_deliveries')
    op.drop_index('idx_output_deliveries_status', table_name='agent_output_deliveries')
    op.drop_index('idx_output_deliveries_webhook_event_id', table_name='agent_output_deliveries')
    op.drop_index('idx_output_deliveries_tenant_id', table_name='agent_output_deliveries')
    op.drop_index('idx_output_deliveries_agent_id', table_name='agent_output_deliveries')
    op.drop_index('idx_output_deliveries_config_id', table_name='agent_output_deliveries')
    op.drop_table('agent_output_deliveries')

    # Drop agent_output_configs table
    op.drop_index('idx_output_configs_is_enabled', table_name='agent_output_configs')
    op.drop_index('idx_output_configs_provider', table_name='agent_output_configs')
    op.drop_index('idx_output_configs_tenant_id', table_name='agent_output_configs')
    op.drop_index('idx_output_configs_agent_id', table_name='agent_output_configs')
    op.drop_table('agent_output_configs')
    
    # Drop enums
    sa.Enum(name='deliverystatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='outputprovider').drop(op.get_bind(), checkfirst=True)
