"""merge 20260415 and 20260417 heads

Revision ID: 588c76a8e630
Revises: 20260415_0001, 20260417_0001
Create Date: 2026-04-17 02:56:47.127122+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '588c76a8e630'
down_revision = ('20260415_0001', '20260417_0001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
