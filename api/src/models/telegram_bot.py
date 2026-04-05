"""Telegram Bot models for agent integration with long polling support."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class TelegramBot(Base):
    """Telegram Bot configuration model with long polling support."""

    __tablename__ = "telegram_bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Bot Configuration
    bot_name = Column(String(255), nullable=False, comment="Display name for the bot")
    bot_username = Column(String(255), nullable=True, comment="@username without @ (auto-detected)")
    bot_token = Column(Text, nullable=False, comment="Encrypted bot token from BotFather")
    telegram_bot_id = Column(BigInteger, nullable=True, comment="Telegram's numeric bot ID (auto-detected)")

    # Webhook Configuration (optional, default is long polling)
    use_webhook = Column(Boolean, default=False, nullable=False, comment="Use webhook instead of long polling")
    webhook_url = Column(Text, nullable=True, comment="Webhook URL if use_webhook is true")
    webhook_secret = Column(Text, nullable=True, comment="Encrypted webhook secret for validation")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(
        String(50), default="disconnected", nullable=False, comment="connected, disconnected, error"
    )
    last_connected_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True, comment="Last error message if any")

    # Worker Assignment (for scalable worker pool)
    assigned_worker_id = Column(String(255), nullable=True, comment="ID of the worker managing this bot")
    worker_connected_at = Column(DateTime, nullable=True, comment="When the worker established the connection")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="telegram_bots")
    tenant = relationship("Tenant")
    conversations = relationship("TelegramConversation", back_populates="telegram_bot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TelegramBot {self.bot_name} (@{self.bot_username}, status: {self.connection_status})>"


class TelegramConversation(Base):
    """Mapping between Telegram chats and agent conversations."""

    __tablename__ = "telegram_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_bot_id = Column(
        UUID(as_uuid=True), ForeignKey("telegram_bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Telegram Chat Information
    telegram_chat_id = Column(BigInteger, nullable=False, comment="Telegram chat ID")
    telegram_chat_type = Column(String(50), nullable=False, comment="private, group, supergroup, channel")
    telegram_chat_title = Column(String(255), nullable=True, comment="Chat title for groups/channels")

    # Telegram User Information
    telegram_user_id = Column(BigInteger, nullable=False, comment="Telegram user ID who initiated")
    telegram_user_name = Column(String(255), nullable=True, comment="Username without @")
    telegram_user_display = Column(String(255), nullable=True, comment="Display name (first + last)")

    # Message tracking for replies
    last_bot_message_id = Column(BigInteger, nullable=True, comment="Last message ID sent by bot")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    telegram_bot = relationship("TelegramBot", back_populates="conversations")
    conversation = relationship("Conversation")

    # Unique constraint: one conversation per chat+user combination per bot
    __table_args__ = (
        # This ensures we don't create duplicate conversations for the same chat+user
        {"comment": "Mapping between Telegram chats and agent conversations"},
    )

    def __repr__(self):
        return f"<TelegramConversation chat={self.telegram_chat_id} user={self.telegram_user_id}>"
