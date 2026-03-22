"""
Project Agent Association Model

Database model for linking agents to projects.
Allows agents to be assigned to multiple projects and projects to have multiple agents.
"""

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class ProjectAgent(BaseModel):
    """
    Association model linking agents to projects.

    Attributes:
        project_id: Reference to the project
        agent_id: Reference to the agent

    Note:
        Uses unique constraint on (project_id, agent_id) to prevent duplicates.
        Does not inherit TenantMixin as tenant is enforced through Project and Agent.
    """

    __tablename__ = "project_agents"

    __table_args__ = (UniqueConstraint("project_id", "agent_id", name="uq_project_agent"),)

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the project",
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the agent",
    )

    # Relationships
    project = relationship("Project", back_populates="agents", foreign_keys=[project_id])

    agent = relationship("Agent", foreign_keys=[agent_id], lazy="selectin")

    def __repr__(self) -> str:
        """String representation of project-agent link."""
        return f"<ProjectAgent(project_id={self.project_id}, agent_id={self.agent_id})>"
