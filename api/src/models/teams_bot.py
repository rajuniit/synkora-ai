"""Teams Bot models for agent integration with Microsoft Teams."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class TeamsBot(Base):
    """Teams Bot configuration model for Microsoft Teams integration."""

    __tablename__ = "teams_bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Microsoft Teams Bot Configuration
    bot_name = Column(String(255), nullable=False)
    app_id = Column(String(255), nullable=False, comment="Microsoft App ID")
    app_password = Column(Text, nullable=False, comment="Encrypted Microsoft App Password")
    teams_tenant_id = Column(
        String(255), nullable=True, comment="Microsoft Teams Tenant ID (optional for multi-tenant)"
    )

    # Webhook Configuration
    webhook_url = Column(String(500), nullable=True, comment="Bot Framework messaging endpoint")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(
        String(50), default="disconnected", nullable=False, comment="connected, disconnected, error"
    )
    last_message_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="teams_bots")
    tenant = relationship("Tenant")
    conversations = relationship("TeamsConversation", back_populates="teams_bot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TeamsBot {self.bot_name} (app_id: {self.app_id}, status: {self.connection_status})>"


class TeamsConversation(Base):
    """Mapping between Teams conversations and agent conversations."""

    __tablename__ = "teams_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teams_bot_id = Column(UUID(as_uuid=True), ForeignKey("teams_bots.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)

    # Teams Conversation Information
    teams_conversation_id = Column(String(255), nullable=False, comment="Teams conversation ID")
    teams_user_id = Column(String(255), nullable=False, comment="Teams user ID (AAD object ID)")
    teams_user_name = Column(String(255), nullable=True)
    teams_channel_id = Column(String(255), nullable=True, comment="Channel ID if in a channel")
    teams_team_id = Column(String(255), nullable=True, comment="Team ID if in a team")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    teams_bot = relationship("TeamsBot", back_populates="conversations")
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<TeamsConversation user={self.teams_user_id} conv={self.teams_conversation_id}>"
