"""Add tenant_compute_configs table; clean up agent_computes and platform_settings.

Changes:
  - CREATE tenant_compute_configs (per-tenant backend config)
  - DROP agent_computes.container_id (containers are now ephemeral, no stored ID)
  - DROP platform_settings.compute_container_image (moved to tenant_compute_configs)
  - Rename compute_type value placeholder comment (model already updated)

Revision ID: 20260414_0004
Revises: 20260414_0003
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260414_0004"
down_revision = "20260414_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New table: tenant_compute_configs ───────────────────────────────────
    op.create_table(
        "tenant_compute_configs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        # Backend selector
        sa.Column("backend", sa.String(50), nullable=False, server_default="docker"),
        # Docker
        sa.Column("docker_image", sa.String(200), nullable=False, server_default="python:3.12-slim"),
        sa.Column("docker_pool_min", sa.Integer, nullable=False, server_default="2"),
        sa.Column("docker_pool_max", sa.Integer, nullable=False, server_default="50"),
        # Cloud backends (encrypted JSON)
        sa.Column("lambda_config_encrypted", sa.Text, nullable=True),
        sa.Column("fargate_config_encrypted", sa.Text, nullable=True),
        sa.Column("gcp_run_config_encrypted", sa.Text, nullable=True),
        sa.Column("k8s_config_encrypted", sa.Text, nullable=True),
        # Limits
        sa.Column("max_concurrent_sessions", sa.Integer, nullable=False, server_default="50"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_compute_configs_tenant_id"),
    )
    op.create_index("ix_tenant_compute_configs_tenant_id", "tenant_compute_configs", ["tenant_id"])
    op.create_index("ix_tenant_compute_configs_backend", "tenant_compute_configs", ["backend"])

    # ── Remove container_id from agent_computes (containers are ephemeral now) ─
    op.drop_column("agent_computes", "container_id")

    # ── Remove compute_container_image from platform_settings (moved to tenant config) ─
    op.drop_column("platform_settings", "compute_container_image")


def downgrade() -> None:
    op.add_column(
        "platform_settings",
        sa.Column("compute_container_image", sa.String(200), server_default="python:3.12-slim"),
    )
    op.add_column(
        "agent_computes",
        sa.Column("container_id", sa.Text, nullable=True),
    )
    op.drop_index("ix_tenant_compute_configs_backend", table_name="tenant_compute_configs")
    op.drop_index("ix_tenant_compute_configs_tenant_id", table_name="tenant_compute_configs")
    op.drop_table("tenant_compute_configs")
