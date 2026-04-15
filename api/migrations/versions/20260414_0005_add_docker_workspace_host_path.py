"""Add docker_workspace_host_path to tenant_compute_configs.

The tenant pool backend needs a configurable host filesystem base path
so operators can mount a dedicated volume (e.g. /data/agent-workspaces)
rather than using the default /agent-workspaces root.

Revision ID: 20260414_0005
Revises: 20260414_0004
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260414_0005"
down_revision = "20260414_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_compute_configs",
        sa.Column(
            "docker_workspace_host_path",
            sa.String(500),
            nullable=False,
            server_default="/agent-workspaces",
            comment="Host filesystem base path where per-agent workspaces are stored",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_compute_configs", "docker_workspace_host_path")
