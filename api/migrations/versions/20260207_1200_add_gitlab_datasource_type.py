"""Add GITLAB to datasourcetype enum

Revision ID: add_gitlab_datasource
Revises: add_tenant_domain_fields
Create Date: 2026-02-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_gitlab_datasource'
down_revision = 'add_tenant_domain_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add GITLAB value to datasourcetype enum
    # Using raw SQL as PostgreSQL requires ALTER TYPE for enum modifications
    op.execute("ALTER TYPE datasourcetype ADD VALUE IF NOT EXISTS 'GITLAB'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly.
    # To properly downgrade, you would need to:
    # 1. Create a new enum without GITLAB
    # 2. Update the column to use the new enum
    # 3. Drop the old enum
    # 4. Rename the new enum
    # This is typically not done in practice as it's complex and risky.
    pass
