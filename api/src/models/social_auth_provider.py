"""
Social Auth Provider model.

Stores configuration for social authentication providers (Google, GitHub, Microsoft, Apple).
"""

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class SocialAuthProvider(BaseModel):
    """
    Social Authentication Provider configuration model.

    Stores OAuth configuration for social login providers.
    Can be configured per tenant or globally.
    """

    __tablename__ = "social_auth_providers"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Tenant ID (null for global/platform-wide config)",
    )

    provider_name = Column(
        String(50),
        nullable=False,
        comment="Provider name: google, github, microsoft, apple",
    )

    client_id = Column(
        String(500),
        nullable=False,
        comment="OAuth client ID",
    )

    client_secret = Column(
        String(1000),
        nullable=False,
        comment="Encrypted OAuth client secret",
    )

    redirect_uri = Column(
        String(500),
        nullable=False,
        comment="OAuth redirect URI",
    )

    # Additional provider-specific configuration (JSON string)
    config = Column(
        String(2000),
        nullable=True,
        comment="JSON string of additional provider-specific configuration",
    )

    enabled = Column(
        String(10),
        nullable=False,
        default="true",
        comment="Whether this provider is enabled",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
    )

    # Constraints - one config per provider per tenant
    __table_args__ = (UniqueConstraint("tenant_id", "provider_name", name="uq_tenant_provider"),)

    def __repr__(self) -> str:
        """String representation."""
        return f"<SocialAuthProvider(id={self.id}, provider={self.provider_name}, tenant_id={self.tenant_id})>"


class AccountProvider(BaseModel):
    """
    Account Provider link model.

    Links user accounts to multiple authentication providers.
    Allows users to sign in with multiple social accounts.
    """

    __tablename__ = "account_providers"

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account ID",
    )

    provider = Column(
        String(50),
        nullable=False,
        comment="Provider name: local, google, github, microsoft, apple, okta",
    )

    provider_user_id = Column(
        String(255),
        nullable=False,
        comment="User ID from the provider",
    )

    provider_email = Column(
        String(255),
        nullable=True,
        comment="Email from the provider (may differ from account email)",
    )

    provider_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional provider data as JSON",
    )

    connected_at = Column(
        String(50),
        nullable=False,
        comment="Timestamp when provider was connected",
    )

    last_used_at = Column(
        String(50),
        nullable=True,
        comment="Timestamp when this provider was last used for login",
    )

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="linked_providers",
    )

    # Constraints - one provider account per user
    __table_args__ = (
        UniqueConstraint("account_id", "provider", name="uq_account_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AccountProvider(id={self.id}, account_id={self.account_id}, provider={self.provider})>"
