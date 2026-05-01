"""add erasure_requests table for GDPR Article 17 right-to-erasure

Revision ID: 20260430_0003
Revises: 20260426_0001
Create Date: 2026-04-30 00:03:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260430_0003"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "erasure_requests"):
        op.create_table(
            "erasure_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            # No FK constraints — account may be anonymised after erasure;
            # this audit row must outlive the erasure operation itself.
            sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("erased_summary", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index("ix_erasure_requests_account_id", "erasure_requests", ["account_id"])
        op.create_index("ix_erasure_requests_tenant_id", "erasure_requests", ["tenant_id"])
        op.create_index("ix_erasure_requests_status", "erasure_requests", ["status"])
        # Composite index used by the 24-hour rate-limit check in the controller
        op.create_index(
            "ix_erasure_requests_account_status_created",
            "erasure_requests",
            ["account_id", "status", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_erasure_requests_account_status_created", table_name="erasure_requests")
    op.drop_index("ix_erasure_requests_status", table_name="erasure_requests")
    op.drop_index("ix_erasure_requests_tenant_id", table_name="erasure_requests")
    op.drop_index("ix_erasure_requests_account_id", table_name="erasure_requests")
    op.drop_table("erasure_requests")
