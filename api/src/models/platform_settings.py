"""
Platform Settings Model - Global configuration for the entire platform
"""

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class PlatformSettings(BaseModel):
    """
    Platform-level settings model.

    Stores global configuration that applies to all tenants.
    Only accessible by platform administrators.
    Typically there's only one record (super tenant settings).
    """

    __tablename__ = "platform_settings"

    # Tenant reference - null for super admin/default settings
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Tenant ID (null for super admin default settings)",
    )

    # Stripe Configuration
    stripe_secret_key = Column(
        Text,
        nullable=True,
        comment="Encrypted Stripe secret key",
    )

    stripe_publishable_key = Column(
        String(500),
        nullable=True,
        comment="Stripe publishable key (not encrypted, safe to expose)",
    )

    stripe_webhook_secret = Column(
        Text,
        nullable=True,
        comment="Encrypted Stripe webhook signing secret",
    )

    stripe_enabled = Column(
        String(10),
        nullable=False,
        default="false",
        comment="Whether Stripe integration is enabled",
    )

    # Payment Gateway Configuration (for future expansion)
    payment_gateway = Column(
        String(50),
        nullable=False,
        default="stripe",
        comment="Active payment gateway: stripe, paypal, etc.",
    )

    # Platform Branding
    platform_name = Column(
        String(255),
        nullable=True,
        comment="Platform name for branding",
    )

    platform_logo_url = Column(
        String(500),
        nullable=True,
        comment="Platform logo URL",
    )

    support_email = Column(
        String(255),
        nullable=True,
        comment="Platform support email",
    )

    primary_color = Column(
        String(7),
        nullable=True,
        default="#3498db",
        comment="Primary brand color (hex)",
    )

    secondary_color = Column(
        String(7),
        nullable=True,
        default="#2c3e50",
        comment="Secondary brand color (hex)",
    )

    # Feature Flags (Global)
    features_enabled = Column(
        Text,
        nullable=True,
        comment="JSON string of enabled platform features",
    )

    # Email Configuration
    smtp_host = Column(
        String(255),
        nullable=True,
        comment="SMTP server host",
    )

    smtp_port = Column(
        String(10),
        nullable=True,
        comment="SMTP server port",
    )

    smtp_username = Column(
        String(255),
        nullable=True,
        comment="SMTP username",
    )

    smtp_password = Column(
        Text,
        nullable=True,
        comment="Encrypted SMTP password",
    )

    smtp_from_email = Column(
        String(255),
        nullable=True,
        comment="Default from email address",
    )

    smtp_from_name = Column(
        String(255),
        nullable=True,
        comment="Default from name",
    )

    # Storage Configuration
    storage_provider = Column(
        String(50),
        nullable=False,
        default="s3",
        comment="Storage provider: s3, minio, local, etc.",
    )

    storage_config = Column(
        Text,
        nullable=True,
        comment="JSON string of storage provider configuration",
    )

    # Analytics & Monitoring
    analytics_enabled = Column(
        String(10),
        nullable=False,
        default="false",
        comment="Whether analytics tracking is enabled",
    )

    analytics_config = Column(
        Text,
        nullable=True,
        comment="JSON string of analytics configuration",
    )

    # Rate Limiting (Global defaults)
    rate_limit_config = Column(
        Text,
        nullable=True,
        comment="JSON string of global rate limiting configuration",
    )

    # Maintenance Mode
    maintenance_mode = Column(
        String(10),
        nullable=False,
        default="false",
        comment="Whether platform is in maintenance mode",
    )

    maintenance_message = Column(
        Text,
        nullable=True,
        comment="Message to display during maintenance",
    )

    # Application Configuration
    app_base_url = Column(
        String(500),
        nullable=True,
        comment="Base URL of the frontend application (e.g., https://app.example.com or https://synkora.ai)",
    )

    # Custom Configuration (extensible)
    custom_config = Column(
        Text,
        nullable=True,
        comment="JSON string for additional custom configuration",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<PlatformSettings(id={self.id}, stripe_enabled={self.stripe_enabled})>"

    @property
    def is_stripe_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return (
            self.stripe_enabled == "true"
            and self.stripe_secret_key is not None
            and self.stripe_publishable_key is not None
            and self.stripe_webhook_secret is not None
        )

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dict, always excluding sensitive fields."""
        exclude = exclude or set()
        # Always exclude encrypted/sensitive fields
        exclude.update(
            {
                "stripe_secret_key",
                "stripe_webhook_secret",
                "smtp_password",
                "storage_config",  # May contain credentials
            }
        )
