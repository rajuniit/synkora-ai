"""
Base model classes and mixins.

This module provides base classes and mixins for all database models,
including common fields, utilities, and serialization methods.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr

from src.core.database import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Record creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="Record last update timestamp",
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier",
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Abstract base model with common fields and methods.

    All models should inherit from this class to get:
    - UUID primary key
    - created_at and updated_at timestamps
    - Common utility methods
    """

    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_") + "s"

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude: Set of field names to exclude from output

        Returns:
            dict: Model data as dictionary

        Example:
            ```python
            user = User(name="John", email="john@example.com")
            data = user.to_dict(exclude={"password_hash"})
            ```
        """
        exclude = exclude or set()
        result = {}

        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert datetime to ISO format
                if isinstance(value, datetime):
                    value = value.isoformat()
                # Convert UUID to string
                elif isinstance(value, uuid.UUID):
                    value = str(value)
                result[column.name] = value

        return result

    # SECURITY: Default fields that should never be mass-assigned
    _PROTECTED_FIELDS = {
        "id",
        "created_at",
        "updated_at",
        "tenant_id",  # Prevents cross-tenant attacks
        "password_hash",
        "password_encrypted",
        "api_key",
        "secret",
        "token",
        "status",
        "deleted_at",
        "is_admin",
        "is_platform_admin",
        "role",
        "permissions",
        "two_factor_secret",
        "reset_token",
        "verification_token",
    }

    def update_from_dict(self, data: dict[str, Any], exclude: set[str] | None = None) -> None:
        """
        Update model instance from dictionary.

        SECURITY: By default, excludes sensitive fields to prevent mass assignment attacks.
        Additional fields can be excluded by passing the exclude parameter.

        Args:
            data: Dictionary with field values
            exclude: Additional field names to exclude from update (merged with default protected fields)

        Example:
            ```python
            user.update_from_dict({"name": "Jane", "email": "jane@example.com"})
            ```
        """
        # SECURITY: Merge with protected fields to prevent mass assignment of sensitive fields
        protected = self._PROTECTED_FIELDS.copy()
        if exclude:
            protected.update(exclude)

        for key, value in data.items():
            if key not in protected and hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TenantMixin:
    """Mixin for multi-tenant models."""

    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp",
    )

    deleted_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who deleted the record",
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self, user_id: uuid.UUID | None = None) -> None:
        """
        Soft delete the record.

        Args:
            user_id: ID of user performing the deletion
        """
        self.deleted_at = datetime.now(UTC)
        if user_id:
            self.deleted_by = user_id

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.deleted_at = None
        self.deleted_by = None


class StatusMixin:
    """Mixin for status field."""

    status = Column(
        String(50),
        nullable=False,
        default="ACTIVE",
        index=True,
        comment="Record status",
    )

    @property
    def is_active(self) -> bool:
        """Check if record is active."""
        return self.status == "ACTIVE"
