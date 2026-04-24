"""add conversation_shares table

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24 00:01:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "conversation_shares"):
        op.create_table(
            "conversation_shares",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("share_token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["accounts.id"], ondelete="CASCADE"),
        )

        op.create_index(
            "ix_conversation_shares_token_hash",
            "conversation_shares",
            ["share_token_hash"],
            unique=True,
        )
        op.create_index(
            "ix_conversation_shares_conversation_id",
            "conversation_shares",
            ["conversation_id", "revoked_at"],
        )
        op.create_index("ix_conversation_shares_tenant_id", "conversation_shares", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_conversation_shares_tenant_id", table_name="conversation_shares")
    op.drop_index("ix_conversation_shares_conversation_id", table_name="conversation_shares")
    op.drop_index("ix_conversation_shares_token_hash", table_name="conversation_shares")
    op.drop_table("conversation_shares")
