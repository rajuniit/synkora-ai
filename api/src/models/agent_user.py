"""
Agent User Model

Links accounts to agents they interact with, tracking usage and engagement.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import backref, relationship

from .base import BaseModel


class AgentUser(BaseModel):
    """
    Agent user model - links accounts to agents they interact with.

    Tracks which users interact with which agents, along with usage metrics.
    The actual user data is stored in the accounts table.
    """

    __tablename__ = "agent_users"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent ID",
    )

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account ID (references central accounts table)",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID (agent owner)",
    )

    source = Column(
        String(50),
        nullable=False,
        index=True,
        comment="How user discovered/accessed agent (widget, api, slack, public_page, etc.)",
    )

    source_details = Column(
        JSONB,
        nullable=True,
        comment="Source-specific details (widget_id, channel_id, referrer, etc.)",
    )

    session_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of conversation sessions",
    )

    message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total messages sent",
    )

    user_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional tracking metadata (preferences, tags, etc.)",
    )

    notes = Column(
        Text,
        nullable=True,
        comment="Internal notes about this user's interaction with the agent",
    )

    # Relationships
    agent = relationship("Agent", backref=backref("agent_users", passive_deletes=True))
    account = relationship("Account", backref="agent_interactions")
    tenant = relationship("Tenant")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentUser(id={self.id}, agent_id={self.agent_id}, account_id={self.account_id})>"

    def increment_session(self) -> None:
        """Increment session count."""
        self.session_count += 1

    def increment_messages(self, count: int = 1) -> None:
        """Increment message count."""
        self.message_count += count
