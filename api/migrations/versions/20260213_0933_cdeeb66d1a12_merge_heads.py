"""merge_heads

Revision ID: cdeeb66d1a12
Revises: add_gitlab_datasource, add_telegram_integration
Create Date: 2026-02-13 09:33:04.909043+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cdeeb66d1a12'
down_revision = ('add_gitlab_datasource', 'add_telegram_integration')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
