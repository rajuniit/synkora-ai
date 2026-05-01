"""SAML 2.0 configuration per tenant."""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class SAMLConfig(BaseModel):
    """
    SAML 2.0 IdP configuration for a tenant.

    One record per tenant (enforced by unique constraint on tenant_id).
    Supports both metadata-URL and raw-XML IdP configuration paths.
    """

    __tablename__ = "saml_configs"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Owning tenant — one SAML config per tenant",
    )

    # IdP metadata — supply URL *or* raw XML; URL is resolved at runtime
    idp_metadata_url = Column(
        String(500),
        nullable=True,
        comment="URL to fetch IdP metadata XML (mutually exclusive with idp_metadata_xml)",
    )
    idp_metadata_xml = Column(
        Text,
        nullable=True,
        comment="Raw IdP metadata XML (used when URL is not available)",
    )

    # SP (Service Provider) settings
    sp_entity_id = Column(
        String(500),
        nullable=False,
        comment="SP Entity ID / Issuer (e.g. https://app.example.com/saml/metadata)",
    )
    acs_url = Column(
        String(500),
        nullable=False,
        comment="Assertion Consumer Service URL where IdP posts SAML responses",
    )

    # Attribute mapping
    email_attribute = Column(
        String(100),
        nullable=False,
        default="email",
        comment="SAML attribute name that contains the user email",
    )
    name_attribute = Column(
        String(100),
        nullable=True,
        default="displayName",
        comment="SAML attribute name that contains the user display name",
    )

    # Behaviour flags
    jit_provisioning = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Auto-create accounts on first successful SAML login (JIT provisioning)",
    )
    force_saml = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="If True, password-based login is disabled for this tenant",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether SAML SSO is enabled for this tenant",
    )
