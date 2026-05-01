"""agent_name unique constraint scoped to tenant

Revision ID: 20260430_0007
Revises: 20260426_0001
Create Date: 2026-04-30 00:07:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0007"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old global unique index on agent_name alone
    op.drop_index("agents_agent_name_idx", table_name="agents", if_exists=True)

    # Create composite unique constraint: agent_name is unique per tenant
    op.create_unique_constraint("uq_agent_name_tenant", "agents", ["agent_name", "tenant_id"])


def downgrade() -> None:
    op.drop_constraint("uq_agent_name_tenant", "agents", type_="unique")
    op.create_index("agents_agent_name_idx", "agents", ["agent_name"], unique=True)
