"""
Human Contact Model

Database model for storing human team members that agents can escalate to.
Each human contact can be linked to agents and receive notifications via
Slack, WhatsApp, or Email.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import BaseModel, TenantMixin


class HumanContact(BaseModel, TenantMixin):
    """
    Human contact model for storing team members.

    Attributes:
        name: Full name of the human contact
        email: Email address for notifications
        slack_user_id: Slack user ID for DM notifications
        slack_workspace_id: Slack workspace/team ID
        whatsapp_number: WhatsApp phone number for notifications
        account_id: Optional link to a Synkora user account
        preferred_channel: Preferred notification channel (slack/whatsapp/email)
        is_active: Whether this contact is active
        tenant_id: Tenant identifier for multi-tenancy
    """

    __tablename__ = "human_contacts"

    name = Column(String(255), nullable=False, comment="Full name of the contact")

    email = Column(String(255), nullable=True, index=True, comment="Email address for notifications")

    slack_user_id = Column(
        String(100), nullable=True, index=True, comment="Slack user ID for DM notifications (e.g., U1234567890)"
    )

    slack_workspace_id = Column(String(100), nullable=True, comment="Slack workspace/team ID")

    whatsapp_number = Column(
        String(50), nullable=True, comment="WhatsApp phone number with country code (e.g., +1234567890)"
    )

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to Synkora user account",
    )

    preferred_channel = Column(
        String(50), nullable=False, default="email", comment="Preferred notification channel: slack, whatsapp, or email"
    )

    is_active = Column(Boolean, nullable=False, default=True, comment="Whether this contact is active")

    timezone = Column(String(100), nullable=True, default="UTC", comment="Timezone for scheduling notifications")

    notification_preferences = Column(
        String(50), nullable=False, default="all", comment="Notification level: all, urgent_only, none"
    )

    def __repr__(self) -> str:
        """String representation of contact."""
        return f"<HumanContact(id={self.id}, name='{self.name}', email='{self.email}')>"

    @property
    def has_slack(self) -> bool:
        """Check if Slack notifications are configured."""
        return bool(self.slack_user_id and self.slack_workspace_id)

    @property
    def has_whatsapp(self) -> bool:
        """Check if WhatsApp notifications are configured."""
        return bool(self.whatsapp_number)

    @property
    def has_email(self) -> bool:
        """Check if email notifications are configured."""
        return bool(self.email)

    def get_available_channels(self) -> list[str]:
        """Get list of available notification channels."""
        channels = []
        if self.has_email:
            channels.append("email")
        if self.has_slack:
            channels.append("slack")
        if self.has_whatsapp:
            channels.append("whatsapp")
        return channels
