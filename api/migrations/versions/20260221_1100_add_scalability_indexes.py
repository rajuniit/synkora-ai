"""Add scalability indexes for high-load performance.

This migration adds critical composite indexes identified during scalability analysis:
- activity_logs: (tenant_id, created_at DESC) for efficient log queries
- credit_transactions: (tenant_id, created_at DESC) for billing queries
- documents: (knowledge_base_id, status) for RAG document filtering

These indexes prevent full table scans under high load in K8s deployments.

Revision ID: 20260221_1100
Revises: 20260221_1000
Create Date: 2026-02-21

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260221_1100"
down_revision = "20260221_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ActivityLog: Composite index for efficient date-range queries per tenant
    # Optimizes: SELECT * FROM activity_logs WHERE tenant_id = ? AND created_at BETWEEN ? AND ? ORDER BY created_at DESC
    op.create_index(
        "ix_activity_logs_tenant_created",
        "activity_logs",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # CreditTransaction: Composite index for billing queries
    # Optimizes: SELECT * FROM credit_transactions WHERE tenant_id = ? ORDER BY created_at DESC
    op.create_index(
        "ix_credit_transactions_tenant_created",
        "credit_transactions",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # CreditTransaction: Index for balance lookups
    # Optimizes: SELECT * FROM credit_transactions WHERE credit_balance_id = ? ORDER BY created_at
    op.create_index(
        "ix_credit_transactions_balance_created",
        "credit_transactions",
        ["credit_balance_id", "created_at"],
        unique=False,
    )

    # Documents: Composite index for RAG queries filtering by status
    # Optimizes: SELECT * FROM documents WHERE knowledge_base_id = ? AND status = ?
    op.create_index(
        "ix_documents_kb_status",
        "documents",
        ["knowledge_base_id", "status"],
        unique=False,
    )

    # DocumentSegments: Index for RAG retrieval
    # Optimizes: SELECT * FROM document_segments WHERE document_id = ?
    op.create_index(
        "ix_document_segments_document_id",
        "document_segments",
        ["document_id"],
        unique=False,
    )

    # AgentKnowledgeBase: Composite index for active knowledge bases
    # Optimizes: SELECT * FROM agent_knowledge_bases WHERE agent_id = ? AND is_active = true
    op.create_index(
        "ix_agent_knowledge_bases_agent_active",
        "agent_knowledge_bases",
        ["agent_id", "is_active"],
        unique=False,
    )

    # ScheduledTask: Index for due tasks query
    # Optimizes: SELECT * FROM scheduled_tasks WHERE is_active = true AND next_run_at <= ?
    op.create_index(
        "ix_scheduled_tasks_active_next_run",
        "scheduled_tasks",
        ["is_active", "next_run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_tasks_active_next_run", table_name="scheduled_tasks")
    op.drop_index("ix_agent_knowledge_bases_agent_active", table_name="agent_knowledge_bases")
    op.drop_index("ix_document_segments_document_id", table_name="document_segments")
    op.drop_index("ix_documents_kb_status", table_name="documents")
    op.drop_index("ix_credit_transactions_balance_created", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_tenant_created", table_name="credit_transactions")
    op.drop_index("ix_activity_logs_tenant_created", table_name="activity_logs")
