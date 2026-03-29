"""
Agent Rating Model

Database model for storing user ratings (likes/dislikes) for agents.
"""

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from src.models.base import BaseModel


class AgentRating(BaseModel):
    """
    Agent rating model for storing user likes/dislikes.

    Attributes:
        agent_id: UUID of the agent being rated
        user_id: Identifier for the user (email, session ID, or user UUID)
        rating: Rating type ('like' or 'dislike')
    """

    __tablename__ = "agent_ratings"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent being rated",
    )

    user_id = Column(String(255), nullable=False, index=True, comment="User identifier (email, session ID, or UUID)")

    rating = Column(String(20), nullable=False, comment="Rating type: 'like' or 'dislike'")

    # Relationships
    agent = relationship("Agent", backref=backref("ratings", passive_deletes=True))

    # Constraints
    __table_args__ = (UniqueConstraint("agent_id", "user_id", name="uq_agent_user_rating"),)

    def __repr__(self) -> str:
        """String representation of rating."""
        return f"<AgentRating(agent_id={self.agent_id}, user_id='{self.user_id}', rating='{self.rating}')>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """
        Convert to dictionary.

        Args:
            exclude: Fields to exclude

        Returns:
            Dictionary representation
        """
        return super().to_dict(exclude=exclude)
