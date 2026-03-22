"""
Team Invitation Model

Database model for managing email-based team invitations with tokens.
"""

import secrets
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class InvitationStatus(StrEnum):
    """Invitation status values."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class TeamInvitation(BaseModel):
    """
    Team invitation model for email-based team member invitations.

    Allows tenant owners/admins to invite new members via email.
    Invitations have expiry dates and unique tokens for security.
    """

    __tablename__ = "team_invitations"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )

    email = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Invitee email address",
    )

    role = Column(
        String(50),
        nullable=False,
        comment="Role to assign upon acceptance (OWNER/ADMIN/EDITOR/MEMBER)",
    )

    invited_by = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Account ID of inviter",
    )

    token = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique invitation token",
    )

    status = Column(
        SQLEnum(InvitationStatus),
        nullable=False,
        default=InvitationStatus.PENDING,
        index=True,
        comment="Invitation status",
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Invitation expiry timestamp",
    )

    accepted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when invitation was accepted",
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when invitation was revoked",
    )

    # Relationships
    tenant = relationship("Tenant", backref="invitations")
    inviter = relationship("Account", foreign_keys=[invited_by])

    def __repr__(self) -> str:
        """String representation."""
        return f"<TeamInvitation(id={self.id}, email={self.email}, status={self.status})>"

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token for invitation."""
        return secrets.token_urlsafe(32)

    @classmethod
    def create_invitation(
        cls,
        tenant_id: str,
        email: str,
        role: str,
        invited_by: str,
        expiry_days: int = 7,
    ) -> "TeamInvitation":
        """
        Create a new team invitation.

        Args:
            tenant_id: Tenant ID
            email: Invitee email
            role: Role to assign
            invited_by: Inviter account ID
            expiry_days: Days until expiry (default 7)

        Returns:
            TeamInvitation: New invitation instance
        """
        return cls(
            tenant_id=tenant_id,
            email=email,
            role=role,
            invited_by=invited_by,
            token=cls.generate_token(),
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=expiry_days),
        )

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == InvitationStatus.PENDING and not self.is_expired

    def accept(self) -> None:
        """Mark invitation as accepted."""
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.now(UTC)

    def revoke(self) -> None:
        """Revoke the invitation."""
        self.status = InvitationStatus.REVOKED
        self.revoked_at = datetime.now(UTC)

    def mark_expired(self) -> None:
        """Mark invitation as expired."""
        self.status = InvitationStatus.EXPIRED
