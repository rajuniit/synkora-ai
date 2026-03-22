"""
Agent Sub-Agent Junction Table Model

Manages parent-child relationships between agents for multi-agent systems.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AgentSubAgent(BaseModel):
    """
    Junction table for parent-child agent relationships.

    Enables multi-agent systems by defining which agents can be invoked
    as sub-agents by a parent agent.
    """

    __tablename__ = "agent_sub_agents"

    parent_agent_id = Column(UUID, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_agent_id = Column(UUID, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    sub_agent = relationship("Agent", foreign_keys=[sub_agent_id], lazy="select")
    parent_agent = relationship("Agent", foreign_keys=[parent_agent_id], lazy="select")

    # ADK workflow execution config
    execution_config = Column(
        JSONB,
        nullable=True,
        comment="""ADK-style execution configuration for workflow agents:
        - input_keys: List of state keys this agent needs as input (e.g., ["topic", "previous_draft"])
        - output_key: State key where this agent's output will be stored (e.g., "blog_content")
        - condition: Optional condition for execution (e.g., {"state_key": "review_status", "value": "needs_revision"})
        - timeout_seconds: Max execution time for this sub-agent
        - retry_on_error: Whether to retry if this sub-agent fails
        """,
    )

    # Legacy config field - kept for backward compatibility
    config = Column(JSONB, nullable=True, comment="Legacy config field for backward compatibility")
