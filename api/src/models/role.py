"""
Role Model

Database model for storing roles with granular permissions.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class Role(BaseModel):
    """
    Role model for role-based access control.

    Represents a role that can be assigned to users within a tenant.
    Roles have associated permissions that define what actions users can perform.
    """

    __tablename__ = "roles"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Tenant ID this role belongs to (NULL for system roles)",
    )

    name = Column(String(100), nullable=False, index=True, comment="Role name (e.g., 'Admin', 'Editor', 'Viewer')")

    description = Column(Text, nullable=True, comment="Human-readable description of the role")

    is_system = Column(
        Boolean, nullable=False, default=False, comment="Whether this is a system role (cannot be deleted)"
    )

    is_default = Column(
        Boolean, nullable=False, default=False, comment="Whether this is the default role for new users"
    )

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="role_obj", cascade="all, delete-orphan")

    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self) -> str:
        """String representation."""
        return f"<Role(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dictionary."""
        return super().to_dict(exclude=exclude)
