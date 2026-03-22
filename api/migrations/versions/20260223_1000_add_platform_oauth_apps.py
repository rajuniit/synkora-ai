"""Add platform OAuth apps support.

This migration adds support for platform-level OAuth apps that Synkora provides
as default integrations (GitHub, Slack, GitLab, Zoom, Gmail) that any tenant can use.

Changes:
- oauth_apps.tenant_id: Make nullable (NULL = platform app)
- oauth_apps.is_platform_app: New boolean column to explicitly mark platform apps
- tenants.disabled_platform_oauth_providers: JSON list of disabled platform providers

Revision ID: 20260223_1000
Revises: 20260221_1100
Create Date: 2026-02-23

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_1000"
down_revision = "20260221_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make oauth_apps.tenant_id nullable for platform apps
    op.alter_column(
        "oauth_apps",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=True,
    )

    # 2. Add is_platform_app column to oauth_apps
    op.add_column(
        "oauth_apps",
        sa.Column(
            "is_platform_app",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True for Synkora-provided OAuth apps that any tenant can use",
        ),
    )

    # 3. Add index on is_platform_app for efficient queries
    op.create_index(
        "ix_oauth_apps_is_platform_app",
        "oauth_apps",
        ["is_platform_app"],
        unique=False,
    )

    # 4. Add composite index for platform app lookups by provider
    op.create_index(
        "ix_oauth_apps_platform_provider",
        "oauth_apps",
        ["is_platform_app", "provider"],
        unique=False,
    )

    # 5. Add disabled_platform_oauth_providers column to tenants
    op.add_column(
        "tenants",
        sa.Column(
            "disabled_platform_oauth_providers",
            sa.JSON(),
            nullable=True,
            comment="List of platform OAuth providers disabled for this tenant (e.g., ['github', 'slack'])",
        ),
    )


def downgrade() -> None:
    # Remove tenant column
    op.drop_column("tenants", "disabled_platform_oauth_providers")

    # Remove oauth_apps indexes and column
    op.drop_index("ix_oauth_apps_platform_provider", table_name="oauth_apps")
    op.drop_index("ix_oauth_apps_is_platform_app", table_name="oauth_apps")
    op.drop_column("oauth_apps", "is_platform_app")

    # Make tenant_id NOT NULL again (will fail if platform apps exist)
    op.alter_column(
        "oauth_apps",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
