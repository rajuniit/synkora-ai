"""add_external_user_fields_to_conversations

Revision ID: 4f6f10bce079
Revises: 20260414_0007
Create Date: 2026-04-14 09:50:27.873643+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f6f10bce079'
down_revision = '20260414_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("external_user_id", sa.String(255), nullable=True))
    op.add_column("conversations", sa.Column("external_org_id", sa.String(255), nullable=True))
    op.add_column("conversations", sa.Column("external_user_name", sa.String(255), nullable=True))
    op.create_index("ix_conversations_external_user_id", "conversations", ["external_user_id"])
    op.create_index("ix_conversations_external_org_id", "conversations", ["external_org_id"])
    op.create_index(
        "ix_conversations_agent_external_user",
        "conversations",
        ["agent_id", "external_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_agent_external_user", table_name="conversations")
    op.drop_index("ix_conversations_external_org_id", table_name="conversations")
    op.drop_index("ix_conversations_external_user_id", table_name="conversations")
    op.drop_column("conversations", "external_user_name")
    op.drop_column("conversations", "external_org_id")
    op.drop_column("conversations", "external_user_id")
