"""add_whatsapp_device_link_fields

Revision ID: add_whatsapp_device_link_fields
Revises: add_agent_subscriptions
Create Date: 2026-03-18 10:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_whatsapp_device_link_fields"
down_revision = "add_agent_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add connection_type column (default "cloud_api" for existing rows)
    op.add_column(
        "whatsapp_bots",
        sa.Column("connection_type", sa.String(length=20), nullable=False, server_default="cloud_api"),
    )

    # Add device_link-specific columns
    op.add_column("whatsapp_bots", sa.Column("session_data", sa.Text(), nullable=True))
    op.add_column("whatsapp_bots", sa.Column("linked_phone_number", sa.String(length=50), nullable=True))

    # Make cloud_api-specific columns nullable (they are not needed for device_link bots)
    op.alter_column("whatsapp_bots", "phone_number_id", existing_type=sa.String(length=255), nullable=True)
    op.alter_column(
        "whatsapp_bots", "whatsapp_business_account_id", existing_type=sa.String(length=255), nullable=True
    )
    op.alter_column("whatsapp_bots", "access_token", existing_type=sa.Text(), nullable=True)
    op.alter_column("whatsapp_bots", "verify_token", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # Restore NOT NULL constraints (will fail if any NULL values exist)
    op.alter_column("whatsapp_bots", "verify_token", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("whatsapp_bots", "access_token", existing_type=sa.Text(), nullable=False)
    op.alter_column(
        "whatsapp_bots", "whatsapp_business_account_id", existing_type=sa.String(length=255), nullable=False
    )
    op.alter_column("whatsapp_bots", "phone_number_id", existing_type=sa.String(length=255), nullable=False)

    # Drop new columns
    op.drop_column("whatsapp_bots", "linked_phone_number")
    op.drop_column("whatsapp_bots", "session_data")
    op.drop_column("whatsapp_bots", "connection_type")
