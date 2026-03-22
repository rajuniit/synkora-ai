"""add tenant domain fields for auto-assignment

Revision ID: add_tenant_domain_fields
Revises: add_role_based_agents
Create Date: 2026-02-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tenant_domain_fields'
down_revision = 'add_role_based_agents'
branch_labels = None
depends_on = None


def upgrade():
    # Add domain field for auto-assigning users based on email domain
    op.add_column(
        'tenants',
        sa.Column(
            'domain',
            sa.String(255),
            nullable=True,
            unique=True,
            comment='Email domain for auto-assigning users (e.g., synkora.ai)'
        )
    )
    op.create_index('ix_tenants_domain', 'tenants', ['domain'], unique=True)

    # Add auto_assign_domain_users flag
    op.add_column(
        'tenants',
        sa.Column(
            'auto_assign_domain_users',
            sa.String(10),
            nullable=False,
            server_default='false',
            comment='Whether to auto-assign users with matching email domain'
        )
    )


def downgrade():
    op.drop_column('tenants', 'auto_assign_domain_users')
    op.drop_index('ix_tenants_domain', table_name='tenants')
    op.drop_column('tenants', 'domain')
