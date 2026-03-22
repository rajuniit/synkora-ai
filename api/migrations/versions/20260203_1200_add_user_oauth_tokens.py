"""add user oauth tokens table

Revision ID: add_user_oauth_tokens
Revises: add_adk_workflow_fields
Create Date: 2026-02-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_oauth_tokens'
down_revision = 'add_adk_workflow_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_oauth_tokens table
    op.create_table(
        'user_oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True, comment='User account that owns this token'),
        sa.Column('oauth_app_id', sa.Integer(), sa.ForeignKey('oauth_apps.id', ondelete='CASCADE'), nullable=False, index=True, comment='OAuth app configuration this token belongs to'),
        sa.Column('access_token', sa.Text(), nullable=False, comment='Encrypted access token'),
        sa.Column('refresh_token', sa.Text(), nullable=True, comment='Encrypted refresh token (if provided by OAuth provider)'),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True, comment='Token expiration timestamp'),
        sa.Column('provider_user_id', sa.String(255), nullable=True, comment='User ID from the OAuth provider'),
        sa.Column('provider_email', sa.String(255), nullable=True, comment='Email from the OAuth provider'),
        sa.Column('provider_username', sa.String(255), nullable=True, comment='Username from the OAuth provider'),
        sa.Column('provider_display_name', sa.String(255), nullable=True, comment='Display name from the OAuth provider'),
        sa.Column('scopes', sa.Text(), nullable=True, comment='Comma-separated list of authorized scopes'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Record last update timestamp'),
        sa.UniqueConstraint('account_id', 'oauth_app_id', name='uq_user_oauth_app'),
    )

    # Create additional indexes for common queries
    op.create_index('ix_user_oauth_tokens_provider_email', 'user_oauth_tokens', ['provider_email'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_user_oauth_tokens_provider_email', table_name='user_oauth_tokens')

    # Drop table
    op.drop_table('user_oauth_tokens')
