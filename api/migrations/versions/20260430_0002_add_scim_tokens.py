"""add scim_tokens table for SCIM 2.0 user provisioning

Revision ID: 20260430_0002
Revises: 20260426_0001
Create Date: 2026-04-30

Creates the scim_tokens table that stores hashed bearer tokens used by
identity providers (Okta, Azure AD, etc.) to authenticate SCIM 2.0
provisioning requests.  Plaintext tokens are never stored.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "20260430_0002"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "scim_tokens"):
        op.create_table(
            "scim_tokens",
            sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                pg.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "token_hash",
                sa.String(64),
                nullable=False,
            ),
            sa.Column("description", sa.String(200), nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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
        )

        op.create_index("ix_scim_tokens_tenant_id", "scim_tokens", ["tenant_id"])
        op.create_index("ix_scim_tokens_token_hash", "scim_tokens", ["token_hash"], unique=True)
        op.create_index("ix_scim_tokens_is_active", "scim_tokens", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_scim_tokens_is_active", table_name="scim_tokens")
    op.drop_index("ix_scim_tokens_token_hash", table_name="scim_tokens")
    op.drop_index("ix_scim_tokens_tenant_id", table_name="scim_tokens")
    op.drop_table("scim_tokens")
