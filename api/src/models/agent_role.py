"""
Agent Role Model

Database model for storing agent role templates (PM, QA, BA, etc.).
Roles define the behavior, system prompt templates, and suggested tools for agents.
"""

import enum

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import JSON

from src.models.base import BaseModel, TenantMixin


class AgentRoleType(enum.StrEnum):
    """Predefined role types for agents."""

    PROJECT_MANAGER = "project_manager"
    PRODUCT_OWNER = "product_owner"
    QA_ENGINEER = "qa_engineer"
    CODE_REVIEWER = "code_reviewer"
    BUSINESS_ANALYST = "business_analyst"
    SCRUM_MASTER = "scrum_master"
    TECH_LEAD = "tech_lead"
    CUSTOM = "custom"


class AgentRole(BaseModel, TenantMixin):
    """
    Agent role model for storing role templates.

    Attributes:
        role_type: Type of role (PM, QA, BA, etc.)
        role_name: Human-readable name for the role
        description: Description of what this role does
        system_prompt_template: Template with placeholders like {project_name}, {context}
        suggested_tools: List of tools recommended for this role
        is_system_template: Whether this is a read-only system template
        tenant_id: Tenant identifier for multi-tenancy (null for system templates)
    """

    __tablename__ = "agent_roles"

    role_type = Column(String(50), nullable=False, index=True, comment="Role type (project_manager, qa_engineer, etc.)")

    role_name = Column(String(255), nullable=False, comment="Human-readable role name")

    description = Column(Text, nullable=True, comment="Description of the role's responsibilities")

    system_prompt_template = Column(
        Text,
        nullable=False,
        comment="System prompt template with placeholders: {project_name}, {project_description}, {human_name}",
    )

    suggested_tools = Column(JSON, nullable=True, default=list, comment="List of tool names suggested for this role")

    default_capabilities = Column(
        JSON, nullable=True, default=dict, comment="Default capabilities and permissions for this role"
    )

    is_system_template = Column(
        Boolean, nullable=False, default=False, comment="Whether this is a system-provided template (read-only)"
    )

    def __repr__(self) -> str:
        """String representation of role."""
        return f"<AgentRole(id={self.id}, type='{self.role_type}', name='{self.role_name}')>"

    def render_system_prompt(
        self,
        project_name: str | None = None,
        project_description: str | None = None,
        human_name: str | None = None,
        additional_context: dict | None = None,
    ) -> str:
        """
        Render the system prompt template with provided values.

        SECURITY: Uses safe string replacement instead of str.format() to prevent
        template injection attacks where attackers could access object attributes
        via {obj.__class__.__bases__} etc.

        Args:
            project_name: Name of the project
            project_description: Description of the project
            human_name: Name of the linked human contact
            additional_context: Additional key-value pairs for template

        Returns:
            Rendered system prompt string
        """
        context = {
            "project_name": project_name or "Unknown Project",
            "project_description": project_description or "No description provided",
            "human_name": human_name or "your human counterpart",
        }

        if additional_context:
            # SECURITY: Only allow string values to prevent object injection
            for key, value in additional_context.items():
                if isinstance(value, str):
                    context[key] = value

        # SECURITY: Use safe string replacement instead of str.format()
        # This prevents attackers from using format string vulnerabilities
        # like {obj.__class__} or {0.__class__.__mro__}
        result = self.system_prompt_template
        for key, value in context.items():
            # Only replace simple {key} patterns, not nested access
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))

        return result
