"""Followup Models

Database models for tracking followup items and their history.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class FollowupStatus(StrEnum):
    """Followup status enum"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class FollowupPriority(StrEnum):
    """Followup priority enum"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FollowupSourceType(StrEnum):
    """Followup source type enum"""

    SLACK_MESSAGE = "slack_message"
    SLACK_THREAD = "slack_thread"
    EMAIL = "email"
    MANUAL = "manual"


class FollowupItem(Base):
    """Followup Item Model - Tracks items requiring followup"""

    __tablename__ = "followup_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core fields
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    initial_message = Column(Text, nullable=False)

    # Source information
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)
    source_url = Column(String(1000), nullable=True)
    channel_id = Column(String(255), nullable=True)
    channel_name = Column(String(255), nullable=True)

    # People involved
    assignee = Column(String(255), nullable=True, index=True)
    mentioned_users = Column(JSONB, nullable=True)
    mentioned_user_names = Column(JSONB, nullable=True)

    # Status and priority
    status = Column(String(50), nullable=False, default="pending", index=True)
    priority = Column(String(20), nullable=False, default="medium", index=True)

    # Scheduling
    followup_frequency_hours = Column(Integer, nullable=False, default=24)
    max_followup_attempts = Column(Integer, nullable=False, default=3)
    current_attempt_count = Column(Integer, nullable=False, default=0)
    last_followup_at = Column(DateTime(timezone=True), nullable=True)
    next_followup_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Completion tracking
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_reason = Column(String(500), nullable=True)
    response_text = Column(Text, nullable=True)

    # Escalation
    escalated = Column(Boolean, nullable=False, default=False)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalation_targets = Column(JSONB, nullable=True)

    # Additional context
    context = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="followup_items")
    agent = relationship("Agent", back_populates="followup_items")
    history = relationship(
        "FollowupHistory",
        back_populates="followup_item",
        cascade="all, delete-orphan",
        order_by="FollowupHistory.sent_at.desc()",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_id": str(self.agent_id),
            "title": self.title,
            "description": self.description,
            "initial_message": self.initial_message,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "assignee": self.assignee,
            "mentioned_users": self.mentioned_users,
            "mentioned_user_names": self.mentioned_user_names,
            "status": self.status,
            "priority": self.priority,
            "followup_frequency_hours": self.followup_frequency_hours,
            "max_followup_attempts": self.max_followup_attempts,
            "current_attempt_count": self.current_attempt_count,
            "last_followup_at": self.last_followup_at.isoformat() if self.last_followup_at else None,
            "next_followup_at": self.next_followup_at.isoformat() if self.next_followup_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completion_reason": self.completion_reason,
            "response_text": self.response_text,
            "escalated": self.escalated,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "escalation_targets": self.escalation_targets,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FollowupHistory(Base):
    """Followup History Model - Tracks each followup attempt"""

    __tablename__ = "followup_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    followup_item_id = Column(
        UUID(as_uuid=True), ForeignKey("followup_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Attempt details
    attempt_number = Column(Integer, nullable=False)
    message_sent = Column(Text, nullable=False)
    message_channel = Column(String(50), nullable=False)

    # AI context
    ai_reasoning = Column(Text, nullable=True)
    ai_tone = Column(String(50), nullable=True)

    # Timing
    sent_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Response tracking
    response_received = Column(Boolean, nullable=False, default=False)
    response_at = Column(DateTime(timezone=True), nullable=True)
    response_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    followup_item = relationship("FollowupItem", back_populates="history")

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "followup_item_id": str(self.followup_item_id),
            "attempt_number": self.attempt_number,
            "message_sent": self.message_sent,
            "message_channel": self.message_channel,
            "ai_reasoning": self.ai_reasoning,
            "ai_tone": self.ai_tone,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "response_received": self.response_received,
            "response_at": self.response_at.isoformat() if self.response_at else None,
            "response_text": self.response_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FollowupConfig(Base):
    """Followup Configuration Model - Agent-specific followup settings"""

    __tablename__ = "followup_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Default settings
    default_followup_frequency_hours = Column(Integer, nullable=False, default=24)
    default_max_attempts = Column(Integer, nullable=False, default=3)

    # Monitoring settings
    monitoring_keywords = Column(JSONB, nullable=True)
    monitored_channels = Column(JSONB, nullable=True)
    escalation_targets = Column(JSONB, nullable=True)

    # Working hours
    working_hours_only = Column(Boolean, nullable=False, default=True)
    timezone = Column(String(50), nullable=False, default="UTC")
    quiet_hours_start = Column(String(5), nullable=True)
    quiet_hours_end = Column(String(5), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="followup_configs")
    agent = relationship("Agent", back_populates="followup_config", uselist=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "agent_id": str(self.agent_id),
            "default_followup_frequency_hours": self.default_followup_frequency_hours,
            "default_max_attempts": self.default_max_attempts,
            "monitoring_keywords": self.monitoring_keywords,
            "monitored_channels": self.monitored_channels,
            "escalation_targets": self.escalation_targets,
            "working_hours_only": self.working_hours_only,
            "timezone": self.timezone,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
