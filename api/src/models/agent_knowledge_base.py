"""Agent Knowledge Base association model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.knowledge_base import KnowledgeBase


class AgentKnowledgeBase(BaseModel, TimestampMixin):
    """Association between agents and knowledge bases."""

    __tablename__ = "agent_knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Retrieval configuration for this agent-KB pair
    retrieval_config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    # Example config:
    # {
    #     "max_results": 5,
    #     "min_score": 0.7,
    #     "max_context_tokens": 4000,
    #     "rerank": true,
    #     "include_metadata": true
    # }

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="knowledge_bases")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="agents")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentKnowledgeBase(agent_id={self.agent_id}, kb_id={self.knowledge_base_id})>"
