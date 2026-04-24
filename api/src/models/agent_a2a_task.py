"""Agent A2A Task model for Google A2A Protocol task tracking."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.core.database import Base


class A2ATaskStatus(enum.StrEnum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AgentA2ATask(Base):
    """
    Persists an A2A protocol task for async agent execution.

    Lifecycle:
      SUBMITTED → WORKING → COMPLETED / FAILED
      SUBMITTED → CANCELED (client cancels)
      WORKING → INPUT_REQUIRED → WORKING (agent needs clarification)
    """

    __tablename__ = "agent_a2a_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)

    # Client-supplied or server-generated task identifier (stable across polls)
    task_id = Column(String(255), nullable=False, unique=True, index=True)

    # Conversation context ID for multi-turn continuity
    context_id = Column(String(255), nullable=False, default=lambda: str(uuid.uuid4()))

    status = Column(String(50), nullable=False, default=A2ATaskStatus.SUBMITTED)

    # A2A message format: {"role": "user", "parts": [{"type": "text", "text": "..."}]}
    input_message = Column(JSONB, nullable=False, default=dict)

    output_text = Column(String, nullable=True)

    error_code = Column(String(100), nullable=True)
    error_message = Column(String(2000), nullable=True)

    # Caller metadata: {"ip": "...", "caller_agent_id": "..."}
    caller_info = Column(JSONB, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_a2a_task_agent_status", "agent_id", "status"),
        Index("ix_a2a_task_tenant_status", "tenant_id", "status"),
    )
