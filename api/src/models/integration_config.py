"""
Integration Configuration Model - Flexible configuration for all integrations
"""

from sqlalchemy import Boolean, Column, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class IntegrationConfig(BaseModel):
    """
    Integration configuration model.

    Stores configuration for various integrations (email, payment, storage, etc.)
    in a flexible, JSON-based format. Supports multi-tenant configurations.

    - tenant_id = null: Super admin default settings
    - tenant_id = <uuid>: Tenant-specific override settings
    """

    __tablename__ = "integration_configs"

    # Tenant reference - null for super admin/default settings
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Tenant ID (null for super admin default settings)",
    )

    # Integration identification
    integration_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Integration type: email, payment, storage, analytics, monitoring, etc.",
    )

    provider = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Provider name: smtp, sendgrid, stripe, s3, etc.",
    )

    # Configuration data (JSON)
    config_data = Column(
        Text,
        nullable=False,
        comment="JSON configuration with encrypted credentials",
    )

    # Status flags
    is_active = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this configuration is currently active",
    )

    is_default = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default config for this integration type",
    )

    is_platform_config = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a platform-level configuration (applies to all tenants)",
    )

    # Metadata
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who created this configuration",
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "integration_type",
            "provider",
            "is_default",
            name="uq_integration_config_tenant_type_provider_default",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<IntegrationConfig("
            f"tenant_id={self.tenant_id}, "
            f"type={self.integration_type}, "
            f"provider={self.provider}, "
            f"active={self.is_active})>"
        )

    def to_dict(self, exclude: set[str] | None = None, include_config: bool = False) -> dict:
        """
        Convert to dict.

        Args:
            exclude: Set of field names to exclude
            include_config: Whether to include config_data (default: False for security)
        """
        exclude = exclude or set()

        # By default, exclude config_data for security
        if not include_config:
            exclude.add("config_data")

        data = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert UUID to string for JSON serialization
                if isinstance(value, UUID):
                    value = str(value)
                data[column.name] = value

        return data
