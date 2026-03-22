"""
Agent Webhook Models

Database models for agent webhook configurations and event logs.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AgentWebhook(BaseModel):
    """
    Agent Webhook Configuration.

    Stores webhook configurations for agents to be triggered by external events.

    Attributes:
        agent_id: Associated agent ID
        name: Webhook name/description
        provider: Webhook provider (github, clickup, jira, slack, custom)
        event_type: Event type to listen for (pr.opened, issue.created, etc.)
        webhook_url: Unique webhook URL for this configuration
        secret: Webhook secret for signature verification (encrypted)
        is_active: Whether webhook is active
        config: Additional webhook configuration (filters, conditions)
        headers: Custom headers to expect (optional)
        retry_config: Retry configuration for failed webhooks
    """

    __tablename__ = "agent_webhooks"

    agent_id = Column(UUID, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True, comment="Agent ID")

    name = Column(String(255), nullable=False, comment="Webhook name/description")

    provider = Column(
        String(50), nullable=False, index=True, comment="Webhook provider (github, clickup, jira, slack, custom)"
    )

    event_types = Column(
        JSONB, nullable=True, comment="Event types to listen for (e.g., ['pull_request', 'issue', 'task_updated'])"
    )

    webhook_url = Column(String(500), nullable=False, unique=True, index=True, comment="Unique webhook URL endpoint")

    secret = Column(Text, nullable=True, comment="Encrypted webhook secret for signature verification")

    is_active = Column(Boolean, nullable=False, default=True, index=True, comment="Whether webhook is active")

    config = Column(JSONB, nullable=True, comment="Additional webhook configuration (filters, conditions, mappings)")

    retry_config = Column(
        JSONB,
        nullable=True,
        default={"max_retries": 3, "retry_delay": 60},
        comment="Retry configuration for failed webhook processing",
    )

    success_count = Column(Integer, nullable=False, default=0, comment="Number of successful webhook events processed")

    failure_count = Column(Integer, nullable=False, default=0, comment="Number of failed webhook events")

    last_triggered_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of last trigger")

    # Relationships
    agent = relationship("Agent", backref="webhooks")

    events = relationship(
        "AgentWebhookEvent",
        back_populates="webhook",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="AgentWebhookEvent.created_at.desc()",
    )

    # Indexes
    __table_args__ = (Index("idx_webhook_active_provider", "is_active", "provider"),)

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentWebhook(id={self.id}, agent_id={self.agent_id}, provider='{self.provider}')>"


class AgentWebhookEvent(BaseModel):
    """
    Agent Webhook Event Log.

    Stores individual webhook event deliveries and their processing status.

    Attributes:
        webhook_id: Associated webhook configuration ID
        event_id: External event ID (from provider)
        event_type: Type of event
        payload: Full webhook payload
        headers: Request headers
        signature: Webhook signature for verification
        status: Processing status (pending, processing, success, failed, retry)
        error_message: Error message if failed
        retry_count: Number of retry attempts
        processed_at: When the event was processed
        agent_execution_id: Associated agent execution/conversation ID
        response_data: Agent's response data
    """

    __tablename__ = "agent_webhook_events"

    webhook_id = Column(
        UUID,
        ForeignKey("agent_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Webhook configuration ID",
    )

    event_id = Column(String(255), nullable=True, index=True, comment="External event ID from provider")

    event_type = Column(String(100), nullable=False, index=True, comment="Event type")

    payload = Column(JSONB, nullable=False, comment="Full webhook payload")

    parsed_data = Column(JSONB, nullable=True, comment="Parsed webhook data")

    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="Processing status (pending, processing, success, failed, retry)",
    )

    error_message = Column(Text, nullable=True, comment="Error message if processing failed")

    retry_count = Column(Integer, nullable=False, default=0, comment="Number of retry attempts")

    agent_execution_id = Column(String(255), nullable=True, comment="Associated agent execution/conversation ID")

    processing_started_at = Column(DateTime(timezone=True), nullable=True, comment="When processing started")

    processing_completed_at = Column(DateTime(timezone=True), nullable=True, comment="When processing completed")

    # Relationships
    webhook = relationship("AgentWebhook", back_populates="events")

    # Indexes
    __table_args__ = (
        Index("idx_webhook_event_status", "webhook_id", "status"),
        Index("idx_webhook_event_created", "webhook_id", "created_at"),
        Index("idx_event_type_status", "event_type", "status"),
        # Composite index for replay protection check: WHERE webhook_id = ? AND event_id = ?
        Index("idx_webhook_event_delivery_id", "webhook_id", "event_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentWebhookEvent(id={self.id}, webhook_id={self.webhook_id}, status='{self.status}')>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dictionary."""
        data = super().to_dict(exclude=exclude)

        # Add human-readable timestamps
        if self.processing_completed_at:
            data["processing_completed_at_formatted"] = (
                self.processing_completed_at.isoformat() if isinstance(self.processing_completed_at, datetime) else None
            )

        return data
