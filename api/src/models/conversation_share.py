"""
ConversationShare model for time-limited, publicly accessible conversation links.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDMixin


class ConversationShare(Base, UUIDMixin, TimestampMixin):
    """
    Represents a shareable link to a conversation.

    The plaintext token is never stored. Only its SHA-256 hash is persisted so
    that a compromised database cannot be used to reconstruct share URLs.
    """

    __tablename__ = "conversation_shares"

    __table_args__ = (
        Index("ix_conversation_shares_token_hash", "share_token_hash", unique=True),
        Index("ix_conversation_shares_conversation_id", "conversation_id", "revoked_at"),
    )

    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)

    # SHA-256 hex digest of the plaintext token — the raw token is never stored
    share_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    @property
    def is_active(self) -> bool:
        """True when the link has not been revoked and has not expired."""
        return self.revoked_at is None and self.expires_at > datetime.now(UTC)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "created_by": str(self.created_by),
            "expires_at": self.expires_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
