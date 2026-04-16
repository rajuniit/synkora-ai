"""Add compute default columns to platform_settings.

Revision ID: 20260414_0002
Revises: 20260414_0001
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20260414_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "platform_settings",
        sa.Column("compute_ssh_known_hosts", sa.Text(), nullable=True, comment="SSH known_hosts content for strict host-key verification"),
    )
    op.add_column(
        "platform_settings",
        sa.Column("compute_default_timeout", sa.String(20), nullable=False, server_default="300", comment="Default per-command timeout in seconds"),
    )
    op.add_column(
        "platform_settings",
        sa.Column("compute_default_max_output", sa.String(20), nullable=False, server_default="8000", comment="Default max stdout characters per remote command"),
    )
    op.add_column(
        "platform_settings",
        sa.Column("compute_default_base_path", sa.String(500), nullable=False, server_default="/tmp/agent_workspace", comment="Default working directory on remote compute targets"),
    )


def downgrade() -> None:
    op.drop_column("platform_settings", "compute_default_base_path")
    op.drop_column("platform_settings", "compute_default_max_output")
    op.drop_column("platform_settings", "compute_default_timeout")
    op.drop_column("platform_settings", "compute_ssh_known_hosts")
