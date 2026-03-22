"""merge_message_ordering_and_load_testing

Revision ID: 41f25b970c7a
Revises: 20260227_1030, add_load_testing_tables
Create Date: 2026-03-04 08:17:29.698039+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "41f25b970c7a"
down_revision = ("20260227_1030", "add_load_testing_tables")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
