"""
Role Permission Model

Database model for mapping permissions to roles within tenants.
"""

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class RolePermission(BaseModel):
    """
    Role Permission model for assigning permissions to roles.

    Maps permissions to specific roles, optionally scoped to a tenant.
    This allows for flexible permission management where roles can have
    different permissions in different tenants.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_id_permission"),)

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Role ID reference",
    )

    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Permission ID",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        comment="Tenant ID (NULL for platform-wide permissions)",
    )

    # Relationships
    role_obj = relationship("Role", back_populates="role_permissions")

    permission = relationship("Permission", back_populates="role_permissions")

    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self) -> str:
        """String representation."""
        return f"<RolePermission(role_id='{self.role_id}', permission_id={self.permission_id})>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dictionary."""
        return super().to_dict(exclude=exclude)
