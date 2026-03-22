"""Agent MCP Server association model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.mcp_server import MCPServer


class AgentMCPServer(BaseModel, TimestampMixin):
    """Association between agents and MCP servers."""

    __tablename__ = "agent_mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mcp_server_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Configuration for this agent-MCP pair
    mcp_config: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    # Example config:
    # {
    #     "enabled_tools": ["tool1", "tool2"],  # Optional: filter specific tools
    #     "timeout": 30,  # Request timeout in seconds
    #     "max_retries": 3,  # Max retry attempts
    #     "tool_config": {  # Per-tool configuration
    #         "tool1": {"param": "value"}
    #     }
    # }

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="mcp_servers")
    mcp_server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="agents")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentMCPServer(agent_id={self.agent_id}, mcp_server_id={self.mcp_server_id})>"
