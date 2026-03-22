"""
Agent Output Configuration Models.

This module defines models for configuring where and how agent responses
should be routed (Slack, Email, Webhook, etc.).
"""

import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, TenantMixin


class OutputProvider(enum.StrEnum):
    """Output provider types."""

    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    MS_TEAMS = "ms_teams"
    DISCORD = "discord"


class DeliveryStatus(enum.StrEnum):
    """Delivery status for output attempts."""

    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentOutputConfig(BaseModel, TenantMixin):
    """
    Configuration for agent output routing.

    Defines where agent responses should be sent (e.g., Slack channel,
    email address, webhook URL). Multiple output configs can exist per agent.
    """

    __tablename__ = "agent_output_configs"

    # Foreign keys
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    oauth_app_id = Column(
        Integer, ForeignKey("oauth_apps.id", ondelete="SET NULL"), nullable=True, index=True
    )  # For Slack/Email via OAuth

    # Output configuration
    provider = Column(Enum(OutputProvider), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # User-friendly name
    description = Column(Text, nullable=True)

    # Provider-specific configuration (JSON)
    # For Slack: {"channel_id": "C123", "channel_name": "#general"}
    # For Email: {"recipients": ["user@example.com"], "subject_template": "..."}
    # For Webhook: {"url": "https://...", "headers": {...}, "method": "POST"}
    config = Column(JSON, nullable=False)

    # Conditional routing (optional)
    # Example: {"webhook_event_type": "github.pull_request"}
    conditions = Column(JSON, nullable=True)

    # Output formatting
    # Template for formatting the output before sending
    # Uses Jinja2 syntax: "New response from {{agent_name}}: {{response}}"
    output_template = Column(Text, nullable=True)

    # Status and settings
    is_enabled = Column(Boolean, default=True, nullable=False)
    send_on_webhook_trigger = Column(Boolean, default=True, nullable=False)
    send_on_chat_completion = Column(Boolean, default=False, nullable=False)

    # Error handling
    retry_on_failure = Column(Boolean, default=True, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Relationships
    agent = relationship("Agent", backref="output_configs")
    oauth_app = relationship("OAuthApp", backref="agent_outputs")
    deliveries = relationship("AgentOutputDelivery", back_populates="output_config", cascade="all, delete-orphan")

    def to_dict(self, include_stats=False):
        """Convert to dictionary."""
        data = {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "oauth_app_id": self.oauth_app_id,
            "tenant_id": str(self.tenant_id),
            "provider": self.provider.value if self.provider else None,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "conditions": self.conditions,
            "output_template": self.output_template,
            "is_enabled": self.is_enabled,
            "send_on_webhook_trigger": self.send_on_webhook_trigger,
            "send_on_chat_completion": self.send_on_chat_completion,
            "retry_on_failure": self.retry_on_failure,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_stats and hasattr(self, "deliveries"):
            total = len(self.deliveries)
            delivered = sum(1 for d in self.deliveries if d.status == DeliveryStatus.DELIVERED)
            failed = sum(1 for d in self.deliveries if d.status == DeliveryStatus.FAILED)
            data["stats"] = {
                "total_deliveries": total,
                "successful": delivered,
                "failed": failed,
                "success_rate": (delivered / total * 100) if total > 0 else 0,
            }

        return data

    def __repr__(self):
        return f"<AgentOutputConfig {self.provider}:{self.name} (agent:{self.agent_id})>"


class AgentOutputDelivery(BaseModel, TenantMixin):
    """
    Tracks individual delivery attempts for agent outputs.

    Stores the delivery status, attempt count, errors, and metadata
    for each time an agent response is sent to a configured output.
    """

    __tablename__ = "agent_output_deliveries"

    # Foreign keys
    output_config_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_output_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    webhook_event_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_webhook_events.id", ondelete="SET NULL"), nullable=True, index=True
    )  # If triggered by webhook

    # Delivery information
    status = Column(Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING, index=True)
    provider = Column(Enum(OutputProvider), nullable=False)

    # Content
    formatted_output = Column(Text, nullable=True)  # The formatted message sent
    raw_response = Column(Text, nullable=True)  # Original agent response

    # Delivery metadata
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)  # Stack trace, response codes, etc.

    # Provider response
    provider_response = Column(JSON, nullable=True)  # Response from Slack/Email/Webhook
    provider_message_id = Column(String(500), nullable=True)  # External message ID

    # Relationships
    output_config = relationship("AgentOutputConfig", back_populates="deliveries")
    agent = relationship("Agent")
    webhook_event = relationship("AgentWebhookEvent")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "output_config_id": str(self.output_config_id),
            "agent_id": str(self.agent_id),
            "webhook_event_id": str(self.webhook_event_id) if self.webhook_event_id else None,
            "tenant_id": str(self.tenant_id),
            "status": self.status.value if self.status else None,
            "provider": self.provider.value if self.provider else None,
            "formatted_output": self.formatted_output,
            "raw_response": self.raw_response,
            "attempt_count": self.attempt_count,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "provider_response": self.provider_response,
            "provider_message_id": self.provider_message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AgentOutputDelivery {self.provider}:{self.status} (config:{self.output_config_id})>"
