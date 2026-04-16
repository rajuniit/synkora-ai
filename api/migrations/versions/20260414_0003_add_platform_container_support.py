"""Add platform_container compute type support.

Adds:
  - agent_computes.container_id    — Docker container ID for platform-managed containers
  - platform_settings.compute_container_image — Docker image used when provisioning containers

Revision ID: 20260414_0003
Revises: 20260414_0002
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20260414_0003"
down_revision = "20260414_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_computes",
        sa.Column(
            "container_id",
            sa.Text(),
            nullable=True,
            comment="Docker container ID for platform_container compute type",
        ),
    )
    op.add_column(
        "platform_settings",
        sa.Column(
            "compute_container_image",
            sa.String(200),
            nullable=False,
            server_default="python:3.12-slim",
            comment="Docker image used when provisioning platform containers for agents",
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_settings", "compute_container_image")
    op.drop_column("agent_computes", "container_id")
