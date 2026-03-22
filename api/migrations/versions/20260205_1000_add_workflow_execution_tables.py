"""add workflow execution tables

Revision ID: add_workflow_execution_tables
Revises: add_conversation_memory_fields
Create Date: 2026-02-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_workflow_execution_tables'
down_revision = 'add_conversation_memory_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        # Foreign keys
        sa.Column('parent_agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True),

        # User and workflow type
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('workflow_type', sa.String(50), nullable=False,
                  comment='Type of workflow: sequential, parallel, loop, custom'),

        # Initial input
        sa.Column('initial_input', sa.Text(), nullable=False,
                  comment='Initial user input that triggered the workflow'),

        # Workflow state
        sa.Column('workflow_state', postgresql.JSONB(), nullable=False, default={},
                  comment='Current workflow state dictionary'),

        # Execution tracking
        sa.Column('status', sa.String(20), nullable=False, default='pending',
                  comment='pending, running, paused, completed, failed, cancelled'),
        sa.Column('current_step_index', sa.Integer(), nullable=False, default=0,
                  comment='Index of current/next sub-agent to execute'),
        sa.Column('total_steps', sa.Integer(), nullable=False, default=0,
                  comment='Total number of sub-agents in workflow'),

        # Timing
        sa.Column('started_at', sa.String(50), nullable=True,
                  comment='When execution started (ISO format)'),
        sa.Column('completed_at', sa.String(50), nullable=True,
                  comment='When execution completed (ISO format)'),

        # Results
        sa.Column('execution_log', postgresql.JSONB(), nullable=False, default=[],
                  comment='Mirrors BaseWorkflowExecutor.execution_log'),
        sa.Column('final_result', postgresql.JSONB(), nullable=True,
                  comment='Final workflow result'),
        sa.Column('error', sa.Text(), nullable=True,
                  comment='Error message if failed'),
    )

    # Create indexes for workflow_executions
    op.create_index('ix_workflow_executions_parent_agent_id', 'workflow_executions', ['parent_agent_id'])
    op.create_index('ix_workflow_executions_conversation_id', 'workflow_executions', ['conversation_id'])
    op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'])
    op.create_index('ix_workflow_executions_status', 'workflow_executions', ['status'])
    op.create_index('ix_workflow_executions_status_tenant', 'workflow_executions', ['status', 'tenant_id'])
    op.create_index('ix_workflow_executions_agent_status', 'workflow_executions', ['parent_agent_id', 'status'])

    # Create workflow_step_executions table
    op.create_table(
        'workflow_step_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),

        # Foreign keys
        sa.Column('workflow_execution_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sub_agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),

        # Step position
        sa.Column('step_index', sa.Integer(), nullable=False,
                  comment='Order of this step in the workflow'),
        sa.Column('agent_name', sa.String(255), nullable=False,
                  comment='Name of the sub-agent'),

        # Input/Output
        sa.Column('input_data', sa.Text(), nullable=True,
                  comment='Input provided to the sub-agent'),
        sa.Column('output_data', sa.Text(), nullable=True,
                  comment='Output from the sub-agent'),
        sa.Column('output_key', sa.String(255), nullable=True,
                  comment='State key where output was stored'),

        # Status
        sa.Column('status', sa.String(20), nullable=False, default='pending',
                  comment='pending, running, completed, failed, skipped'),
        sa.Column('error', sa.Text(), nullable=True,
                  comment='Error message if failed'),
        sa.Column('skip_reason', sa.String(500), nullable=True,
                  comment='Reason if step was skipped'),

        # Timing
        sa.Column('started_at', sa.String(50), nullable=True,
                  comment='When step started (ISO format)'),
        sa.Column('completed_at', sa.String(50), nullable=True,
                  comment='When step completed (ISO format)'),

        # Metadata
        sa.Column('execution_metadata', postgresql.JSONB(), nullable=True,
                  comment='Additional execution metadata'),
    )

    # Create indexes for workflow_step_executions
    op.create_index('ix_workflow_step_executions_workflow_execution_id',
                    'workflow_step_executions', ['workflow_execution_id'])
    op.create_index('ix_workflow_step_executions_sub_agent_id',
                    'workflow_step_executions', ['sub_agent_id'])
    op.create_index('ix_workflow_step_executions_status',
                    'workflow_step_executions', ['status'])
    op.create_index('ix_workflow_step_workflow_index',
                    'workflow_step_executions', ['workflow_execution_id', 'step_index'])


def downgrade():
    # Drop workflow_step_executions table
    op.drop_index('ix_workflow_step_workflow_index', table_name='workflow_step_executions')
    op.drop_index('ix_workflow_step_executions_status', table_name='workflow_step_executions')
    op.drop_index('ix_workflow_step_executions_sub_agent_id', table_name='workflow_step_executions')
    op.drop_index('ix_workflow_step_executions_workflow_execution_id', table_name='workflow_step_executions')
    op.drop_table('workflow_step_executions')

    # Drop workflow_executions table
    op.drop_index('ix_workflow_executions_agent_status', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_status_tenant', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_status', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_user_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_conversation_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_parent_agent_id', table_name='workflow_executions')
    op.drop_table('workflow_executions')
