"""WhatsApp Bot models for agent integration with WhatsApp Business API."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class WhatsAppBot(Base):
    """WhatsApp Bot configuration model for WhatsApp Business API."""

    __tablename__ = "whatsapp_bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Connection type: "cloud_api" (Meta Business API) or "device_link" (QR scan)
    connection_type = Column(String(20), default="cloud_api", nullable=False)

    # WhatsApp Business API Configuration (cloud_api only)
    bot_name = Column(String(255), nullable=False)
    phone_number_id = Column(String(255), nullable=True, comment="WhatsApp Business phone number ID")
    whatsapp_business_account_id = Column(String(255), nullable=True, comment="WhatsApp Business Account ID")
    access_token = Column(Text, nullable=True, comment="Encrypted WhatsApp Business API access token")
    verify_token = Column(String(255), nullable=True, comment="Webhook verification token")

    # Device Link fields (device_link only)
    session_data = Column(Text, nullable=True, comment="Encrypted neonize session data for device_link bots")
    linked_phone_number = Column(String(50), nullable=True, comment="Phone number linked via QR scan")

    # Webhook Configuration
    webhook_url = Column(String(500), nullable=True, comment="Webhook callback URL")

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
    agent = relationship("Agent", back_populates="whatsapp_bots")
    tenant = relationship("Tenant")
    conversations = relationship("WhatsAppConversation", back_populates="whatsapp_bot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WhatsAppBot {self.bot_name} (phone: {self.phone_number_id}, status: {self.connection_status})>"


class WhatsAppConversation(Base):
    """Mapping between WhatsApp conversations and agent conversations."""

    __tablename__ = "whatsapp_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_bot_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_bots.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)

    # WhatsApp User Information
    whatsapp_user_id = Column(String(255), nullable=False, comment="WhatsApp user phone number")
    whatsapp_user_name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    whatsapp_bot = relationship("WhatsAppBot", back_populates="conversations")
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<WhatsAppConversation user={self.whatsapp_user_id}>"
