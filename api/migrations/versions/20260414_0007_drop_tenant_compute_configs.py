"""Drop tenant_compute_configs table — no S3, no per-tenant compute config needed.

The sandbox service is platform-level. Workspaces are ephemeral.

Revision ID: 20260414_0007
Revises: 20260414_0006
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260414_0007"
down_revision = "20260414_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_tenant_compute_configs_tenant_id", table_name="tenant_compute_configs")
    op.drop_index("ix_tenant_compute_configs_backend", table_name="tenant_compute_configs", if_exists=True)
    op.drop_table("tenant_compute_configs")


def downgrade() -> None:
    op.create_table(
        "tenant_compute_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("s3_bucket", sa.String(300), nullable=True),
        sa.Column("s3_region", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_compute_configs_tenant_id"),
    )
    op.create_index("ix_tenant_compute_configs_tenant_id", "tenant_compute_configs", ["tenant_id"])
