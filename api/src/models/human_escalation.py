"""
Human Escalation Model

Database model for tracking escalations from agents to humans.
Supports multi-channel notifications (Slack, WhatsApp, Email) and
tracks the full lifecycle of escalations.
"""

import enum

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class EscalationReason(enum.StrEnum):
    """Reasons for escalating to a human."""

    UNCERTAINTY = "uncertainty"
    APPROVAL_NEEDED = "approval_needed"
    COMPLEX_DECISION = "complex_decision"
    BLOCKER = "blocker"
    REVIEW_REQUIRED = "review_required"
    CUSTOMER_REQUEST = "customer_request"
    SECURITY_CONCERN = "security_concern"
    BUDGET_APPROVAL = "budget_approval"


class EscalationStatus(enum.StrEnum):
    """Status of an escalation."""

    PENDING = "pending"
    NOTIFIED = "notified"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EscalationPriority(enum.StrEnum):
    """Priority level of an escalation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class HumanEscalation(BaseModel, TenantMixin):
    """
    Human escalation model for tracking agent-to-human escalations.

    Attributes:
        project_id: Project this escalation belongs to (required)
        conversation_id: Conversation context for the escalation
        from_agent_id: Agent that initiated the escalation
        to_human_id: Human contact to notify
        reason: Reason for escalation
        priority: Urgency level
        subject: Brief subject line
        message: Detailed message for the human
        context_summary: AI-generated summary of conversation context
        status: Current escalation status
        notification_channels: Which channels to use for notification
        notification_sent_at: When notification was sent
        human_response: Response from the human
        resolved_at: When escalation was resolved
        tenant_id: Tenant identifier for multi-tenancy
    """

    __tablename__ = "human_escalations"

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project this escalation belongs to",
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Conversation context for the escalation",
    )

    from_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Agent that initiated the escalation",
    )

    to_human_id = Column(
        UUID(as_uuid=True),
        ForeignKey("human_contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Human contact to notify",
    )

    reason = Column(String(50), nullable=False, index=True, comment="Reason for escalation")

    priority = Column(
        String(20),
        nullable=False,
        default=EscalationPriority.MEDIUM.value,
        index=True,
        comment="Priority level: low, medium, high, urgent",
    )

    subject = Column(String(500), nullable=False, comment="Brief subject line for the escalation")

    message = Column(Text, nullable=False, comment="Detailed message for the human")

    context_summary = Column(Text, nullable=True, comment="AI-generated summary of conversation context")

    status = Column(
        String(50),
        nullable=False,
        default=EscalationStatus.PENDING.value,
        index=True,
        comment="Current escalation status",
    )

    notification_channels = Column(
        JSON,
        nullable=True,
        default=dict,
        comment='Channels used for notification: {"slack": true, "email": true, "whatsapp": false}',
    )

    notification_sent_at = Column(DateTime(timezone=True), nullable=True, comment="When notification was sent")

    notification_metadata = Column(
        JSON, nullable=True, default=dict, comment="Metadata about sent notifications (message IDs, etc.)"
    )

    human_response = Column(Text, nullable=True, comment="Response from the human")

    resolved_at = Column(DateTime(timezone=True), nullable=True, comment="When escalation was resolved")

    resolution_notes = Column(Text, nullable=True, comment="Additional notes about the resolution")

    expires_at = Column(DateTime(timezone=True), nullable=True, comment="When this escalation expires if not addressed")

    # Relationships
    project = relationship("Project", back_populates="escalations", foreign_keys=[project_id])

    conversation = relationship("Conversation", foreign_keys=[conversation_id], lazy="selectin")

    from_agent = relationship("Agent", foreign_keys=[from_agent_id], lazy="selectin")

    to_human = relationship("HumanContact", foreign_keys=[to_human_id], lazy="selectin")

    def __repr__(self) -> str:
        """String representation of escalation."""
        return f"<HumanEscalation(id={self.id}, status='{self.status}', reason='{self.reason}')>"

    @property
    def is_pending(self) -> bool:
        """Check if escalation is pending."""
        return self.status in [
            EscalationStatus.PENDING.value,
            EscalationStatus.NOTIFIED.value,
            EscalationStatus.IN_PROGRESS.value,
        ]

    @property
    def is_resolved(self) -> bool:
        """Check if escalation is resolved."""
        return self.status == EscalationStatus.RESOLVED.value
