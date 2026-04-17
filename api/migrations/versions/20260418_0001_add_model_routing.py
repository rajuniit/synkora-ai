"""add model routing to agents and agent_llm_configs

Revision ID: 20260418_0001
Revises: 588c76a8e630
Create Date: 2026-04-18 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260418_0001"
down_revision = "588c76a8e630"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add routing_mode and routing_config to agents table
    op.add_column(
        "agents",
        sa.Column(
            "routing_mode",
            sa.String(30),
            nullable=False,
            server_default="fixed",
            comment="Model routing mode: fixed | round_robin | cost_opt | intent | latency_opt",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "routing_config",
            JSONB,
            nullable=True,
            comment="Routing configuration: quality_floor, max_cost_per_1k, etc.",
        ),
    )

    # Add routing_rules and routing_weight to agent_llm_configs table
    op.add_column(
        "agent_llm_configs",
        sa.Column(
            "routing_rules",
            JSONB,
            nullable=True,
            comment=(
                "Per-config routing rules: intents, min_complexity, max_complexity, "
                "cost_per_1k_input, cost_per_1k_output, priority, is_fallback"
            ),
        ),
    )
    op.add_column(
        "agent_llm_configs",
        sa.Column(
            "routing_weight",
            sa.Float,
            nullable=True,
            comment="Weight for round_robin/weighted random routing (0.0–1.0, default 1.0)",
        ),
    )

    # Index routing_mode for quick queries filtering by mode
    op.create_index("ix_agents_routing_mode", "agents", ["routing_mode"])


def downgrade() -> None:
    op.drop_index("ix_agents_routing_mode", table_name="agents")
    op.drop_column("agent_llm_configs", "routing_weight")
    op.drop_column("agent_llm_configs", "routing_rules")
    op.drop_column("agents", "routing_config")
    op.drop_column("agents", "routing_mode")
