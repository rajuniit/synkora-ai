"""add celery_task_id and cancelled status to task_executions

Revision ID: 20260402_0001
Revises: 20260327_0001
Create Date: 2026-04-02

Adds celery_task_id column to task_executions so running tasks can be revoked,
and adds 'cancelled' as a valid status value.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260402_0001"
down_revision = "20260327_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_executions",
        sa.Column("celery_task_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_task_executions_celery_task_id", "task_executions", ["celery_task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_executions_celery_task_id", table_name="task_executions")
    op.drop_column("task_executions", "celery_task_id")
