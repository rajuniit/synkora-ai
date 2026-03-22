"""add webhook event delivery id composite index

Revision ID: 20260319_0001
Revises:
Create Date: 2026-03-19

Adds a composite index on (webhook_id, event_id) to support efficient
webhook replay protection checks.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260319_0001"
down_revision = "add_whatsapp_device_link_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_webhook_event_delivery_id",
        "agent_webhook_events",
        ["webhook_id", "event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_webhook_event_delivery_id", table_name="agent_webhook_events")
