"""
Conversation model for managing chat conversations.

A Conversation represents a session of interaction with an AI app.
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class ConversationStatus(enum.StrEnum):
    """Conversation status."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class Conversation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Conversation model representing a chat session.

    Attributes:
        app_id: Foreign key to app
        account_id: Foreign key to account (user)
        name: Conversation name/title
        summary: Conversation summary
        status: Conversation status
        message_count: Number of messages in conversation
    """

    __tablename__ = "conversations"

    # Foreign keys
    app_id: Mapped[UUID | None] = mapped_column(ForeignKey("apps.id"), index=True)
    account_id: Mapped[UUID | None] = mapped_column(ForeignKey("accounts.id"), index=True)
    agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    summary: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(String(255))

    # Status
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, native_enum=False, length=50),
        nullable=False,
        default=ConversationStatus.ACTIVE,
    )

    # Metrics
    message_count: Mapped[int] = mapped_column(default=0)

    # Memory/Context Management
    context_summary: Mapped[str | None] = mapped_column(
        Text, comment="LLM-generated summary of conversation for context continuity"
    )
    summary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the context summary was last updated"
    )
    summary_message_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="Message count when summary was generated (for incremental updates)"
    )
    total_tokens_estimated: Mapped[int] = mapped_column(
        Integer, default=0, comment="Estimated total tokens in conversation history"
    )

    # Relationships
    app: Mapped["App"] = relationship("App", back_populates="conversations")
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="conversations")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    charts: Mapped[list["Chart"]] = relationship("Chart", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Conversation {self.name} ({self.message_count} messages)>"

    def to_dict(self, include_messages: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_messages: Whether to include messages

        Returns:
            Dictionary representation
        """
        data = {
            "id": str(self.id),
            "app_id": str(self.app_id),
            "account_id": str(self.account_id) if self.account_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "session_id": self.session_id,
            "name": self.name,
            "summary": self.summary,
            "status": self.status.value,
            "message_count": self.message_count,
            "context_summary": self.context_summary,
            "summary_updated_at": self.summary_updated_at.isoformat() if self.summary_updated_at else None,
            "summary_message_count": self.summary_message_count,
            "total_tokens_estimated": self.total_tokens_estimated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_messages and self.messages:
            data["messages"] = [msg.to_dict() for msg in self.messages]

        return data

    def is_active(self) -> bool:
        """Check if conversation is active."""
        return self.status == ConversationStatus.ACTIVE and not self.deleted_at

    def increment_message_count(self) -> None:
        """
        Increment message count atomically.

        Uses SQL expression to avoid race conditions under concurrent requests.
        The actual increment happens at flush/commit time via SQL:
        UPDATE conversations SET message_count = message_count + 1 WHERE id = ?

        Without this, two concurrent requests reading message_count=5 would both
        write 6. With SQL expression, the DB handles: 5+1=6, then 6+1=7.
        """
        # Use SQL expression for atomic increment
        self.message_count = Conversation.message_count + 1
