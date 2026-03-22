"""add branding colors to platform settings

Revision ID: add_branding_colors
Revises: 20260214_1000_add_bot_worker_assignment_fields
Create Date: 2026-02-15 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_branding_colors'
down_revision = 'f8e7d6c5b4a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add primary_color column
    op.add_column(
        'platform_settings',
        sa.Column('primary_color', sa.String(7), nullable=True, server_default='#3498db',
                  comment='Primary brand color (hex)')
    )
    # Add secondary_color column
    op.add_column(
        'platform_settings',
        sa.Column('secondary_color', sa.String(7), nullable=True, server_default='#2c3e50',
                  comment='Secondary brand color (hex)')
    )


def downgrade() -> None:
    op.drop_column('platform_settings', 'secondary_color')
    op.drop_column('platform_settings', 'primary_color')
