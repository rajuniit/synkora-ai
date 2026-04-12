"""Add widget identity verification and org-based agent routing

Revision ID: 20260412_0001
Revises: 20260409_0002
Create Date: 2026-04-12

Changes:
- agent_widgets: add identity_secret, identity_verification_required, enable_agent_routing
- widget_agent_routes: new table mapping external org IDs to agents per widget
- conversations: add external_user_id, external_org_id, external_user_name + composite index
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "20260412_0001"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agent_widgets: new columns ────────────────────────────────────────────────
    op.add_column("agent_widgets", sa.Column("identity_secret", sa.Text(), nullable=True))
    op.add_column(
        "agent_widgets",
        sa.Column(
            "identity_verification_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "agent_widgets",
        sa.Column(
            "enable_agent_routing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── widget_agent_routes: new table ────────────────────────────────────────────
    op.create_table(
        "widget_agent_routes",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("widget_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("external_org_id", sa.String(255), nullable=False),
        sa.Column("agent_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["widget_id"], ["agent_widgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("widget_id", "external_org_id", name="uq_widget_org_route"),
    )
    op.create_index(
        "ix_widget_agent_routes_lookup",
        "widget_agent_routes",
        ["widget_id", "external_org_id"],
    )

    # ── conversations: new columns ────────────────────────────────────────────────
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
    # conversations
    op.drop_index("ix_conversations_agent_external_user", table_name="conversations")
    op.drop_index("ix_conversations_external_org_id", table_name="conversations")
    op.drop_index("ix_conversations_external_user_id", table_name="conversations")
    op.drop_column("conversations", "external_user_name")
    op.drop_column("conversations", "external_org_id")
    op.drop_column("conversations", "external_user_id")

    # widget_agent_routes
    op.drop_index("ix_widget_agent_routes_lookup", table_name="widget_agent_routes")
    op.drop_table("widget_agent_routes")

    # agent_widgets
    op.drop_column("agent_widgets", "enable_agent_routing")
    op.drop_column("agent_widgets", "identity_verification_required")
    op.drop_column("agent_widgets", "identity_secret")
