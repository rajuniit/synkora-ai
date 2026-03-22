"""
Workflow Execution Models - Persistent tracking of ADK workflow executions.

These models provide persistence for the BaseWorkflowExecutor system,
enabling workflow resume after interruption and providing audit trails.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class WorkflowExecutionStatus(enum.StrEnum):
    """Status of a workflow execution."""

    PENDING = "pending"  # Created but not started
    RUNNING = "running"  # Currently executing
    PAUSED = "paused"  # Paused (can be resumed)
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Manually cancelled


class WorkflowStepStatus(enum.StrEnum):
    """Status of a workflow step execution."""

    PENDING = "pending"  # Not yet started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed with error
    SKIPPED = "skipped"  # Skipped due to condition


class WorkflowExecution(BaseModel, TenantMixin):
    """
    Persistent record of a workflow execution.

    Tracks the overall state of a multi-agent workflow execution,
    enabling resume after interruption and providing audit trails.

    Integrates with the ADK BaseWorkflowExecutor system.
    """

    __tablename__ = "workflow_executions"

    # The parent workflow agent
    parent_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The workflow agent being executed",
    )

    # Associated conversation (optional - some workflows may not have one)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated conversation",
    )

    # User who triggered the workflow
    user_id = Column(String(255), nullable=False, index=True, comment="User who initiated the workflow")

    # Workflow type (from Agent.workflow_type)
    workflow_type = Column(String(50), nullable=False, comment="Type of workflow: sequential, parallel, loop, custom")

    # Initial input that started the workflow
    initial_input = Column(Text, nullable=False, comment="Initial user input that triggered the workflow")

    # Workflow state (mirrors BaseWorkflowExecutor.state)
    workflow_state = Column(JSONB, nullable=False, default=dict, comment="Current workflow state dictionary")

    # Execution tracking
    status = Column(
        Enum(WorkflowExecutionStatus),
        nullable=False,
        default=WorkflowExecutionStatus.PENDING,
        index=True,
        comment="Current execution status",
    )

    current_step_index = Column(
        Integer, nullable=False, default=0, comment="Index of current/next sub-agent to execute"
    )

    total_steps = Column(Integer, nullable=False, default=0, comment="Total number of sub-agents in workflow")

    # Timing
    started_at = Column(
        String(50),  # ISO format datetime string
        nullable=True,
        comment="When execution started",
    )

    completed_at = Column(
        String(50),  # ISO format datetime string
        nullable=True,
        comment="When execution completed",
    )

    # Results
    execution_log = Column(JSONB, nullable=False, default=list, comment="Mirrors BaseWorkflowExecutor.execution_log")

    final_result = Column(JSONB, nullable=True, comment="Final workflow result")

    error = Column(Text, nullable=True, comment="Error message if failed")

    # Relationships
    parent_agent = relationship("Agent", foreign_keys=[parent_agent_id], lazy="select")

    conversation = relationship("Conversation", foreign_keys=[conversation_id], lazy="select")

    steps = relationship(
        "WorkflowStepExecution",
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        order_by="WorkflowStepExecution.step_index",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_workflow_executions_status_tenant", "status", "tenant_id"),
        Index("ix_workflow_executions_agent_status", "parent_agent_id", "status"),
    )

    def mark_started(self):
        """Mark workflow as started."""
        self.status = WorkflowExecutionStatus.RUNNING
        self.started_at = datetime.now(UTC).isoformat()

    def mark_completed(self, final_result: dict = None):
        """Mark workflow as completed."""
        self.status = WorkflowExecutionStatus.COMPLETED
        self.completed_at = datetime.now(UTC).isoformat()
        if final_result:
            self.final_result = final_result

    def mark_failed(self, error: str):
        """Mark workflow as failed."""
        self.status = WorkflowExecutionStatus.FAILED
        self.completed_at = datetime.now(UTC).isoformat()
        self.error = error

    def mark_paused(self):
        """Mark workflow as paused (can be resumed)."""
        self.status = WorkflowExecutionStatus.PAUSED

    def mark_cancelled(self):
        """Mark workflow as cancelled."""
        self.status = WorkflowExecutionStatus.CANCELLED
        self.completed_at = datetime.now(UTC).isoformat()

    @property
    def is_resumable(self) -> bool:
        """Check if workflow can be resumed."""
        return self.status in (
            WorkflowExecutionStatus.PAUSED,
            WorkflowExecutionStatus.RUNNING,  # May have been interrupted
        )

    @property
    def is_terminal(self) -> bool:
        """Check if workflow is in a terminal state."""
        return self.status in (
            WorkflowExecutionStatus.COMPLETED,
            WorkflowExecutionStatus.FAILED,
            WorkflowExecutionStatus.CANCELLED,
        )


class WorkflowStepExecution(BaseModel):
    """
    Individual sub-agent execution within a workflow.

    Tracks each step of a workflow execution for detailed
    audit trails and potential step-level resume.
    """

    __tablename__ = "workflow_step_executions"

    # Parent workflow execution
    workflow_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent workflow execution",
    )

    # The sub-agent that was executed
    sub_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        comment="The sub-agent that was executed",
    )

    # Step position in workflow
    step_index = Column(Integer, nullable=False, comment="Order of this step in the workflow")

    # Agent name (denormalized for convenience)
    agent_name = Column(String(255), nullable=False, comment="Name of the sub-agent")

    # Input/Output
    input_data = Column(Text, nullable=True, comment="Input provided to the sub-agent")

    output_data = Column(Text, nullable=True, comment="Output from the sub-agent")

    output_key = Column(String(255), nullable=True, comment="State key where output was stored")

    # Status
    status = Column(
        Enum(WorkflowStepStatus),
        nullable=False,
        default=WorkflowStepStatus.PENDING,
        index=True,
        comment="Execution status of this step",
    )

    error = Column(Text, nullable=True, comment="Error message if failed")

    skip_reason = Column(String(500), nullable=True, comment="Reason if step was skipped")

    # Timing
    started_at = Column(String(50), nullable=True, comment="When step started")

    completed_at = Column(String(50), nullable=True, comment="When step completed")

    # Execution metadata
    execution_metadata = Column(JSONB, nullable=True, comment="Additional execution metadata (tokens used, etc.)")

    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="steps")

    sub_agent = relationship("Agent", foreign_keys=[sub_agent_id], lazy="select")

    # Indexes
    __table_args__ = (Index("ix_workflow_step_workflow_index", "workflow_execution_id", "step_index"),)

    def mark_started(self):
        """Mark step as started."""
        self.status = WorkflowStepStatus.RUNNING
        self.started_at = datetime.now(UTC).isoformat()

    def mark_completed(self, output: str = None, output_key: str = None):
        """Mark step as completed."""
        self.status = WorkflowStepStatus.COMPLETED
        self.completed_at = datetime.now(UTC).isoformat()
        if output:
            self.output_data = output
        if output_key:
            self.output_key = output_key

    def mark_failed(self, error: str):
        """Mark step as failed."""
        self.status = WorkflowStepStatus.FAILED
        self.completed_at = datetime.now(UTC).isoformat()
        self.error = error

    def mark_skipped(self, reason: str = None):
        """Mark step as skipped."""
        self.status = WorkflowStepStatus.SKIPPED
        self.completed_at = datetime.now(UTC).isoformat()
        self.skip_reason = reason

    @property
    def duration_seconds(self) -> float | None:
        """Calculate step duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds()
        except (ValueError, TypeError):
            return None
