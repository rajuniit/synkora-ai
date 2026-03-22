"""add role-based agents with human escalation

Revision ID: add_role_based_agents
Revises: add_workflow_execution_tables
Create Date: 2026-02-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_role_based_agents'
down_revision = 'add_workflow_execution_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_roles table
    op.create_table(
        'agent_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('role_type', sa.String(50), nullable=False, index=True,
                  comment='Role type (project_manager, qa_engineer, etc.)'),
        sa.Column('role_name', sa.String(255), nullable=False,
                  comment='Human-readable role name'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Description of the role responsibilities'),
        sa.Column('system_prompt_template', sa.Text(), nullable=False,
                  comment='System prompt template with placeholders: {project_name}, {project_description}, {human_name}'),
        sa.Column('suggested_tools', postgresql.JSONB(), nullable=True, default=[],
                  comment='List of tool names suggested for this role'),
        sa.Column('default_capabilities', postgresql.JSONB(), nullable=True, default={},
                  comment='Default capabilities and permissions for this role'),
        sa.Column('is_system_template', sa.Boolean(), nullable=False, default=False,
                  comment='Whether this is a system-provided template (read-only)'),
    )

    # Create human_contacts table
    op.create_table(
        'human_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('name', sa.String(255), nullable=False,
                  comment='Full name of the contact'),
        sa.Column('email', sa.String(255), nullable=True, index=True,
                  comment='Email address for notifications'),
        sa.Column('slack_user_id', sa.String(100), nullable=True, index=True,
                  comment='Slack user ID for DM notifications (e.g., U1234567890)'),
        sa.Column('slack_workspace_id', sa.String(100), nullable=True,
                  comment='Slack workspace/team ID'),
        sa.Column('whatsapp_number', sa.String(50), nullable=True,
                  comment='WhatsApp phone number with country code (e.g., +1234567890)'),
        sa.Column('account_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Optional link to Synkora user account'),
        sa.Column('preferred_channel', sa.String(50), nullable=False, default='email',
                  comment='Preferred notification channel: slack, whatsapp, or email'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True,
                  comment='Whether this contact is active'),
        sa.Column('timezone', sa.String(100), nullable=True, default='UTC',
                  comment='Timezone for scheduling notifications'),
        sa.Column('notification_preferences', sa.String(50), nullable=False, default='all',
                  comment='Notification level: all, urgent_only, none'),
    )

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('name', sa.String(255), nullable=False, index=True,
                  comment='Project name'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Project description'),
        sa.Column('status', sa.String(50), nullable=False, default='active', index=True,
                  comment='Project status: active, on_hold, completed, archived'),
        sa.Column('knowledge_base_id', sa.Integer(),
                  sa.ForeignKey('knowledge_bases.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Optional shared knowledge base for project context'),
        sa.Column('external_project_ref', postgresql.JSONB(), nullable=True, default={},
                  comment='References to external PM tools: {"jira": "PROJ-KEY", "clickup": "space_id", "github": "owner/repo"}'),
        sa.Column('shared_context', postgresql.JSONB(), nullable=True, default={},
                  comment='Real-time shared state between agents on this project'),
        sa.Column('project_settings', postgresql.JSONB(), nullable=True, default={},
                  comment='Project-specific settings and configurations'),
    )

    # Create project_agents junction table
    op.create_table(
        'project_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),

        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True,
                  comment='Reference to the project'),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True,
                  comment='Reference to the agent'),

        sa.UniqueConstraint('project_id', 'agent_id', name='uq_project_agent'),
    )

    # Create human_escalations table
    op.create_table(
        'human_escalations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),

        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True,
                  comment='Project this escalation belongs to'),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Conversation context for the escalation'),
        sa.Column('from_agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Agent that initiated the escalation'),
        sa.Column('to_human_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('human_contacts.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Human contact to notify'),

        sa.Column('reason', sa.String(50), nullable=False, index=True,
                  comment='Reason for escalation'),
        sa.Column('priority', sa.String(20), nullable=False, default='medium', index=True,
                  comment='Priority level: low, medium, high, urgent'),
        sa.Column('subject', sa.String(500), nullable=False,
                  comment='Brief subject line for the escalation'),
        sa.Column('message', sa.Text(), nullable=False,
                  comment='Detailed message for the human'),
        sa.Column('context_summary', sa.Text(), nullable=True,
                  comment='AI-generated summary of conversation context'),

        sa.Column('status', sa.String(50), nullable=False, default='pending', index=True,
                  comment='Current escalation status'),
        sa.Column('notification_channels', postgresql.JSONB(), nullable=True, default={},
                  comment='Channels used for notification: {"slack": true, "email": true, "whatsapp": false}'),
        sa.Column('notification_sent_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When notification was sent'),
        sa.Column('notification_metadata', postgresql.JSONB(), nullable=True, default={},
                  comment='Metadata about sent notifications (message IDs, etc.)'),

        sa.Column('human_response', sa.Text(), nullable=True,
                  comment='Response from the human'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When escalation was resolved'),
        sa.Column('resolution_notes', sa.Text(), nullable=True,
                  comment='Additional notes about the resolution'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When this escalation expires if not addressed'),
    )

    # Create indexes for human_escalations
    op.create_index('ix_human_escalations_status_tenant', 'human_escalations', ['status', 'tenant_id'])
    op.create_index('ix_human_escalations_project_status', 'human_escalations', ['project_id', 'status'])
    op.create_index('ix_human_escalations_human_status', 'human_escalations', ['to_human_id', 'status'])

    # Add role_id and human_contact_id columns to agents table
    op.add_column(
        'agents',
        sa.Column('role_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agent_roles.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Reference to agent role template')
    )
    op.add_column(
        'agents',
        sa.Column('human_contact_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('human_contacts.id', ondelete='SET NULL'), nullable=True, index=True,
                  comment='Reference to linked human contact for escalation')
    )


def downgrade():
    # Remove columns from agents table
    op.drop_column('agents', 'human_contact_id')
    op.drop_column('agents', 'role_id')

    # Drop human_escalations table
    op.drop_index('ix_human_escalations_human_status', table_name='human_escalations')
    op.drop_index('ix_human_escalations_project_status', table_name='human_escalations')
    op.drop_index('ix_human_escalations_status_tenant', table_name='human_escalations')
    op.drop_table('human_escalations')

    # Drop project_agents table
    op.drop_table('project_agents')

    # Drop projects table
    op.drop_table('projects')

    # Drop human_contacts table
    op.drop_table('human_contacts')

    # Drop agent_roles table
    op.drop_table('agent_roles')
