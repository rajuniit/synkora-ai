"""
Agent Tool Model

Database model for storing agent-specific tool configurations.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AgentTool(BaseModel):
    """
    AgentTool model for storing agent-specific tool configurations.

    Each agent can have multiple tools configured with their own settings.
    Tool configurations are encrypted and stored securely.

    Attributes:
        agent_id: Foreign key to agents table (UUID)
        tool_name: Name of the tool (e.g., 'web_search', 'github', 'GMAIL')
        config: JSONB field storing tool configuration (API keys, settings, etc.)
        enabled: Whether the tool is currently enabled for this agent
    """

    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_id", "tool_name", name="uq_agent_tool"),)

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent ID this tool belongs to",
    )

    tool_name = Column(String(100), nullable=False, index=True, comment="Name of the tool")

    config = Column(JSONB, nullable=False, default=dict, comment="Tool configuration (API keys, settings, etc.)")

    enabled = Column(Boolean, nullable=False, default=True, index=True, comment="Whether the tool is enabled")

    oauth_app_id = Column(
        Integer,
        ForeignKey("oauth_apps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional: Specific OAuth app to use for this tool",
    )

    custom_tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("custom_tools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional: Custom tool (OpenAPI) this agent tool references",
    )

    operation_id = Column(
        String(100), nullable=True, comment="Optional: Specific operation ID from custom tool's OpenAPI schema"
    )

    slack_bot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("slack_bots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional: specific Slack bot to use for this tool",
    )

    # Relationships
    agent = relationship("Agent", back_populates="tools")

    oauth_app = relationship("OAuthApp", foreign_keys=[oauth_app_id])

    custom_tool = relationship("CustomTool", foreign_keys=[custom_tool_id])

    slack_bot = relationship("SlackBot", foreign_keys=[slack_bot_id])

    def __repr__(self) -> str:
        """String representation of agent tool."""
        return f"<AgentTool(id={self.id}, agent_id={self.agent_id}, tool='{self.tool_name}', enabled={self.enabled})>"

    def to_dict(self, include_config: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_config: Whether to include the config (may contain sensitive data)

        Returns:
            Dictionary representation
        """
        data = super().to_dict()

        # Optionally exclude config for security
        if not include_config:
            data.pop("config", None)

        return data
