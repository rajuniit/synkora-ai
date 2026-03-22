"""
Agent Template Model

Pre-built agent configurations that users can clone to quickly get started.
"""

from sqlalchemy import JSON, Boolean, Column, Integer, String, Text

from src.models.base import BaseModel


class AgentTemplate(BaseModel):
    """
    Agent template for pre-built role-based agent configurations.

    These templates are available to all users and can be cloned
    to create new agents with pre-configured system prompts, tools,
    and settings.
    """

    __tablename__ = "agent_templates"

    name = Column(String(255), nullable=False, index=True, comment="Template name")
    slug = Column(String(255), nullable=False, unique=True, index=True, comment="URL-friendly slug")
    description = Column(Text, nullable=True, comment="Template description")
    category = Column(String(100), nullable=False, index=True, comment="Category (Product, Engineering, etc.)")
    system_prompt = Column(Text, nullable=False, comment="System prompt for the agent")
    tags = Column(JSON, nullable=True, default=list, comment="Tags for search/filtering")
    suggested_tools = Column(JSON, nullable=True, default=list, comment="Suggested tool integrations")
    icon = Column(String(50), nullable=True, comment="Icon identifier")
    color = Column(String(20), nullable=True, comment="Theme color hex code")
    is_active = Column(Boolean, nullable=False, default=True, comment="Whether template is visible")
    usage_count = Column(Integer, nullable=False, default=0, comment="Number of times this template has been used")
