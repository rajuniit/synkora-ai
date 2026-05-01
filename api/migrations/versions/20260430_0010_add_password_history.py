"""add password_history to accounts

Revision ID: 20260430_0010
Revises: 20260430_0007
Create Date: 2026-04-30

Adds a JSON column to the accounts table for storing the last 12 bcrypt hashes
used by the account.  The array is prepended on every password change and trimmed
to 12 entries.  Checked during password reset/change to prevent reuse.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260430_0010"
down_revision = "20260430_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Idempotent guard — skip if column already exists
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("accounts")}
    if "password_history" not in existing_cols:
        op.add_column(
            "accounts",
            sa.Column(
                "password_history",
                sa.JSON(),
                nullable=True,
                comment="Last 12 bcrypt password hashes — checked to prevent password reuse",
            ),
        )


def downgrade() -> None:
    op.drop_column("accounts", "password_history")
