"""
Project Model

Database model for lightweight project context.
Projects group agents together and provide shared context without task management.
Task management is handled through existing Jira/ClickUp/GitHub integrations.
"""

import enum

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class ProjectStatus(enum.StrEnum):
    """Project status options."""

    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(BaseModel, TenantMixin):
    """
    Project model for grouping agents and sharing context.

    Attributes:
        name: Project name
        description: Project description
        status: Project status (active, on_hold, completed, archived)
        knowledge_base_id: Optional shared knowledge base for project context
        external_project_ref: References to external PM tools (Jira, ClickUp, GitHub)
        shared_context: Real-time shared state between agents on this project
        tenant_id: Tenant identifier for multi-tenancy
    """

    __tablename__ = "projects"

    name = Column(String(255), nullable=False, index=True, comment="Project name")

    description = Column(Text, nullable=True, comment="Project description")

    status = Column(
        String(50),
        nullable=False,
        default=ProjectStatus.ACTIVE.value,
        index=True,
        comment="Project status: active, on_hold, completed, archived",
    )

    knowledge_base_id = Column(
        Integer,
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional shared knowledge base for project context",
    )

    external_project_ref = Column(
        JSON,
        nullable=True,
        default=dict,
        comment='References to external PM tools: {"jira": "PROJ-KEY", "clickup": "space_id", "github": "owner/repo"}',
    )

    shared_context = Column(
        JSON, nullable=True, default=dict, comment="Real-time shared state between agents on this project"
    )

    project_settings = Column(JSON, nullable=True, default=dict, comment="Project-specific settings and configurations")

    # Relationships
    agents = relationship("ProjectAgent", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

    escalations = relationship("HumanEscalation", back_populates="project", cascade="all, delete-orphan", lazy="select")

    knowledge_base = relationship("KnowledgeBase", foreign_keys=[knowledge_base_id], lazy="selectin")

    def __repr__(self) -> str:
        """String representation of project."""
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"

    def get_context_value(self, key: str, default=None):
        """
        Get a value from shared context.

        Args:
            key: Context key to retrieve
            default: Default value if key not found

        Returns:
            Value from context or default
        """
        if not self.shared_context:
            return default
        return self.shared_context.get(key, default)

    def set_context_value(self, key: str, value) -> None:
        """
        Set a value in shared context.

        Args:
            key: Context key to set
            value: Value to store
        """
        if self.shared_context is None:
            self.shared_context = {}
        self.shared_context[key] = value

    def get_external_ref(self, provider: str) -> str | None:
        """
        Get external project reference for a provider.

        Args:
            provider: Provider name (jira, clickup, github)

        Returns:
            External reference string or None
        """
        if not self.external_project_ref:
            return None
        return self.external_project_ref.get(provider)

    @property
    def is_active(self) -> bool:
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE.value
