"""add adk workflow fields to agents

Revision ID: add_adk_workflow_fields
Revises: 20260122_1400
Create Date: 2026-01-25 01:31:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_adk_workflow_fields'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    # Add workflow fields to agents table
    op.add_column('agents', sa.Column('workflow_type', sa.String(length=50), nullable=True,
                  comment='Workflow type: sequential, loop, parallel, custom (null for regular LLM agents)'))
    op.add_column('agents', sa.Column('workflow_config', postgresql.JSON(), nullable=True,
                  comment='Workflow-specific configuration: loop, parallel, sequential, custom'))

    # Create agent_sub_agents table
    op.create_table(
        'agent_sub_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('parent_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sub_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('execution_order', sa.Integer(), default=0, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('execution_config', postgresql.JSONB(), nullable=True,
                  comment='ADK-style execution configuration for workflow agents'),
        sa.Column('config', postgresql.JSONB(), nullable=True,
                  comment='Legacy config field for backward compatibility'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    # Drop agent_sub_agents table
    op.drop_table('agent_sub_agents')

    # Remove fields from agents table
    op.drop_column('agents', 'workflow_config')
    op.drop_column('agents', 'workflow_type')
