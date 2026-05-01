"""add execution_backend column to agents

Revision ID: 20260426_0001
Revises: 20260424_0002
Create Date: 2026-04-26 00:01:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260426_0001"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Disable statement timeout for this session — ALTER TABLE on large tables
    # can exceed the default timeout set by the connection pool.
    op.execute("SET LOCAL statement_timeout = 0")
    op.add_column(
        "agents",
        sa.Column(
            "execution_backend",
            sa.String(30),
            nullable=False,
            server_default="celery",
            comment="Execution backend: celery | lambda | cloud_run | do_functions",
        ),
    )
    op.create_index("ix_agents_execution_backend", "agents", ["execution_backend"])


def downgrade() -> None:
    op.drop_index("ix_agents_execution_backend", table_name="agents")
    op.drop_column("agents", "execution_backend")
