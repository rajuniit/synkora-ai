"""
Okta Tenant model for SSO configuration.

Stores Okta configuration per organization for enterprise SSO.
"""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class OktaTenant(BaseModel):
    """
    Okta Tenant configuration model.

    Stores Okta OIDC/SAML configuration for enterprise SSO.
    Each tenant can have their own Okta instance.
    """

    __tablename__ = "okta_tenants"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID this Okta config belongs to",
    )

    domain = Column(
        String(255),
        nullable=False,
        comment="Okta domain (e.g., company.okta.com)",
    )

    client_id = Column(
        String(255),
        nullable=False,
        comment="Okta OAuth client ID",
    )

    client_secret = Column(
        String(500),
        nullable=False,
        comment="Encrypted Okta OAuth client secret",
    )

    issuer_url = Column(
        String(500),
        nullable=False,
        comment="Okta issuer URL for token validation",
    )

    authorization_server_id = Column(
        String(255),
        nullable=True,
        comment="Okta authorization server ID (optional, for custom auth servers)",
    )

    # SAML configuration (optional)
    saml_metadata_url = Column(
        String(500),
        nullable=True,
        comment="SAML metadata URL",
    )

    saml_entity_id = Column(
        String(500),
        nullable=True,
        comment="SAML entity ID",
    )

    # JIT provisioning settings
    jit_provisioning_enabled = Column(
        String(10),
        nullable=False,
        default="true",
        comment="Enable just-in-time user provisioning",
    )

    # Role mapping configuration (JSON string)
    role_mapping = Column(
        String(2000),
        nullable=True,
        comment="JSON mapping of Okta groups to Synkora roles",
    )

    # Additional settings
    enabled = Column(
        String(10),
        nullable=False,
        default="true",
        comment="Whether this Okta tenant is enabled",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<OktaTenant(id={self.id}, domain={self.domain}, tenant_id={self.tenant_id})>"
