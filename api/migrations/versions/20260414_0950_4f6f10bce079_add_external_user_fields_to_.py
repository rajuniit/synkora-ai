"""add_external_user_fields_to_conversations

Revision ID: 4f6f10bce079
Revises: 20260414_0007
Create Date: 2026-04-14 09:50:27.873643+00:00

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "4f6f10bce079"
down_revision = "20260414_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These columns and indexes were already added in migration 20260412_0001.
    pass


def downgrade() -> None:
    pass
