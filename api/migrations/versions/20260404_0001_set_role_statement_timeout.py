"""Set statement_timeout as role default for PgBouncer compatibility.

In PgBouncer transaction mode, the SQLAlchemy receive_connect event
(which runs SET statement_timeout = '30s') only affects the single backend
connection that PgBouncer assigns at that moment. Other backend connections
in PgBouncer's pool don't receive the SET.

Setting it as a role default ensures every new backend connection PgBouncer
creates inherits the timeout without any per-connection SET needed.

Revision ID: 20260404_0001
Revises: 20260402_0001
Create Date: 2026-04-04
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260404_0001"
down_revision: str | None = "20260402_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Set statement_timeout as a role-level default.
    # This survives PgBouncer connection reuse — every backend connection
    # that PgBouncer creates for this role gets the timeout automatically.
    # Value matches the hardcoded '30s' in src/core/database.py receive_connect.
    op.execute("ALTER ROLE current_user SET statement_timeout = '30000'")


def downgrade() -> None:
    op.execute("ALTER ROLE current_user RESET statement_timeout")
