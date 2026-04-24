"""add llm_token_usages table

Revision ID: 20260424_0001
Revises: 281062e3d594
Create Date: 2026-04-24 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260424_0001"
down_revision = "281062e3d594"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "llm_token_usages"):
        op.create_table(
            "llm_token_usages",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            # No FK constraints — analytics must survive entity deletions
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model_name", sa.String(255), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cache_read_tokens", sa.Integer(), nullable=True),
            sa.Column("cache_creation_tokens", sa.Integer(), nullable=True),
            sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
            sa.Column("estimated_cost_usd", sa.Numeric(12, 8), nullable=True),
            sa.Column("optimization_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.PrimaryKeyConstraint("id"),
        )

        op.create_index("ix_llm_usage_tenant_id", "llm_token_usages", ["tenant_id"])
        op.create_index("ix_llm_usage_agent_id", "llm_token_usages", ["agent_id"])
        op.create_index("ix_llm_usage_tenant_created", "llm_token_usages", ["tenant_id", "created_at"])
        op.create_index(
            "ix_llm_usage_tenant_agent_created",
            "llm_token_usages",
            ["tenant_id", "agent_id", "created_at"],
        )
        op.create_index("ix_llm_usage_tenant_model", "llm_token_usages", ["tenant_id", "model_name"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_tenant_model", table_name="llm_token_usages")
    op.drop_index("ix_llm_usage_tenant_agent_created", table_name="llm_token_usages")
    op.drop_index("ix_llm_usage_tenant_created", table_name="llm_token_usages")
    op.drop_index("ix_llm_usage_agent_id", table_name="llm_token_usages")
    op.drop_index("ix_llm_usage_tenant_id", table_name="llm_token_usages")
    op.drop_table("llm_token_usages")
