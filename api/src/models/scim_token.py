"""SCIM Bearer Token for IdP authentication.

This module defines the SCIMToken model used to authenticate SCIM 2.0
provisioning requests from identity providers such as Okta and Azure AD.
Tokens are stored as SHA-256 hashes; plaintext is shown only once on creation.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import BaseModel, TenantMixin


class SCIMToken(BaseModel, TenantMixin):
    """
    SCIM Bearer Token for IdP authentication.

    Attributes:
        tenant_id: Tenant this token grants SCIM access to (from TenantMixin)
        token_hash: SHA-256 hex digest of the plaintext token (never stored in plaintext)
        description: Human-readable label, e.g. "Okta provisioning"
        is_active: Whether this token is currently accepted
        last_used_at: Timestamp of the most recent successful authentication
    """

    __tablename__ = "scim_tokens"

    token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hex digest of the plaintext token",
    )

    description = Column(
        String(200),
        nullable=True,
        comment="Human-readable label, e.g. 'Okta provisioning'",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this token is currently accepted",
    )

    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent successful authentication",
    )

    def touch(self) -> None:
        """Update last_used_at to now."""
        self.last_used_at = datetime.now(UTC)

    def __repr__(self) -> str:
        """String representation."""
        return f"<SCIMToken(id={self.id}, tenant_id={self.tenant_id}, active={self.is_active})>"
