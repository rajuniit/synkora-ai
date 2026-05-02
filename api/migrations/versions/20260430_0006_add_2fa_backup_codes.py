"""add two_factor_backup_codes to accounts

Revision ID: 20260430_0006
Revises: 20260430_0005
Create Date: 2026-04-30

Adds a JSON column to the accounts table for storing hashed 2FA backup/recovery
codes.  Each code is stored as a SHA-256 hex digest and removed after first use.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260430_0006"
down_revision = "20260430_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Idempotent guard — skip if column already exists
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("accounts")}
    if "two_factor_backup_codes" not in existing_cols:
        op.add_column(
            "accounts",
            sa.Column(
                "two_factor_backup_codes",
                sa.JSON(),
                nullable=True,
                comment="Hashed 2FA backup/recovery codes (SHA-256); each consumed on use",
            ),
        )


def downgrade() -> None:
    op.drop_column("accounts", "two_factor_backup_codes")
