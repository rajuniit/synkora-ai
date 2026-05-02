"""add saml_configs table for SAML 2.0 SSO

Revision ID: 20260430_0001
Revises: 20260426_0001
Create Date: 2026-04-30

Creates the saml_configs table that stores per-tenant SAML 2.0 IdP configuration,
SP settings, attribute mapping, and JIT provisioning flags.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "20260430_0001"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Skip if already exists (idempotent re-run safety)
    if bind.dialect.has_table(bind, "saml_configs"):
        return

    op.create_table(
        "saml_configs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # IdP metadata
        sa.Column("idp_metadata_url", sa.String(500), nullable=True),
        sa.Column("idp_metadata_xml", sa.Text, nullable=True),
        # SP settings
        sa.Column("sp_entity_id", sa.String(500), nullable=False),
        sa.Column("acs_url", sa.String(500), nullable=False),
        # Attribute mapping
        sa.Column("email_attribute", sa.String(100), nullable=False, server_default="email"),
        sa.Column("name_attribute", sa.String(100), nullable=True, server_default="displayName"),
        # Behaviour flags
        sa.Column("jit_provisioning", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("force_saml", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        # Timestamps
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

    # Index on tenant_id for fast lookup (UNIQUE constraint already implies one,
    # but an explicit named index makes pg_dump / introspection cleaner)
    op.create_index("ix_saml_configs_tenant_id", "saml_configs", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_saml_configs_tenant_id", table_name="saml_configs")
    op.drop_table("saml_configs")
