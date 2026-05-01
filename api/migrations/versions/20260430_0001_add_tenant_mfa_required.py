"""add mfa_required column to tenants

Revision ID: 20260430_0001b
Revises: 20260426_0001
Create Date: 2026-04-30 00:01:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260430_0001b"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.add_column(
        "tenants",
        sa.Column(
            "mfa_required",
            sa.String(10),
            nullable=False,
            server_default="false",
            comment="Whether 2FA is required for all members of this tenant (stored as string)",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "mfa_required")
