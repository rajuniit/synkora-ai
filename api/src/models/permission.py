"""
Permission Model

Database model for storing granular permissions for role-based access control.
"""

from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class Permission(BaseModel):
    """
    Permission model for granular access control.

    Represents a specific permission that can be assigned to roles.
    Permissions follow the format: {resource}.{action}

    Examples:
        - agents.create
        - agents.read
        - agents.update
        - agents.delete
        - team.invite
        - settings.update
    """

    __tablename__ = "permissions"

    name = Column(
        String(255), nullable=False, unique=True, index=True, comment="Permission name (e.g., 'agents.create')"
    )

    resource = Column(
        String(100), nullable=False, index=True, comment="Resource type (e.g., 'agents', 'knowledge_bases')"
    )

    action = Column(String(50), nullable=False, comment="Action type (e.g., 'create', 'read', 'update', 'delete')")

    description = Column(Text, nullable=True, comment="Human-readable description of the permission")

    is_system = Column(Boolean, nullable=False, default=True, comment="Whether this is a system permission (vs custom)")

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Permission(id={self.id}, name='{self.name}')>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dictionary."""
        return super().to_dict(exclude=exclude)
