"""Simplify tenant_compute_configs — one persistent container, S3 workspace only.

Drops all backend/pool/docker/cloud columns added in 0004/0005.
Keeps only s3_bucket and s3_region (per-tenant workspace storage overrides).

Revision ID: 20260414_0006
Revises: 20260414_0005
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "20260414_0006"
down_revision = "20260414_0005"
branch_labels = None
depends_on = None

_DROP_COLS = [
    "backend",
    "docker_image",
    "docker_pool_min",
    "docker_pool_max",
    "docker_workspace_host_path",
    "lambda_config_encrypted",
    "fargate_config_encrypted",
    "gcp_run_config_encrypted",
    "k8s_config_encrypted",
    "max_concurrent_sessions",
]


def upgrade() -> None:
    for col in _DROP_COLS:
        op.drop_column("tenant_compute_configs", col)

    op.add_column(
        "tenant_compute_configs",
        sa.Column("s3_bucket", sa.String(300), nullable=True,
                  comment="S3 bucket for this tenant's agent workspaces"),
    )
    op.add_column(
        "tenant_compute_configs",
        sa.Column("s3_region", sa.String(50), nullable=True,
                  comment="AWS region for the S3 bucket"),
    )


def downgrade() -> None:
    op.drop_column("tenant_compute_configs", "s3_region")
    op.drop_column("tenant_compute_configs", "s3_bucket")

    op.add_column("tenant_compute_configs",
                  sa.Column("backend", sa.String(50), nullable=False, server_default="docker"))
    op.add_column("tenant_compute_configs",
                  sa.Column("docker_image", sa.String(200), nullable=False,
                            server_default="python:3.12-slim"))
    op.add_column("tenant_compute_configs",
                  sa.Column("docker_pool_min", sa.Integer, nullable=False, server_default="2"))
    op.add_column("tenant_compute_configs",
                  sa.Column("docker_pool_max", sa.Integer, nullable=False, server_default="50"))
    op.add_column("tenant_compute_configs",
                  sa.Column("docker_workspace_host_path", sa.String(500), nullable=False,
                            server_default="/agent-workspaces"))
    op.add_column("tenant_compute_configs",
                  sa.Column("lambda_config_encrypted", sa.Text, nullable=True))
    op.add_column("tenant_compute_configs",
                  sa.Column("fargate_config_encrypted", sa.Text, nullable=True))
    op.add_column("tenant_compute_configs",
                  sa.Column("gcp_run_config_encrypted", sa.Text, nullable=True))
    op.add_column("tenant_compute_configs",
                  sa.Column("k8s_config_encrypted", sa.Text, nullable=True))
    op.add_column("tenant_compute_configs",
                  sa.Column("max_concurrent_sessions", sa.Integer, nullable=False,
                            server_default="50"))
