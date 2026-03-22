"""
Human Contact Service

Service for managing human team members that agents can escalate to.
Handles CRUD operations and validation of contact information.
"""

import logging
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import HumanContact

logger = logging.getLogger(__name__)


class HumanContactService:
    """Service for managing human contacts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_contact(
        self,
        tenant_id: UUID,
        name: str,
        email: str | None = None,
        slack_user_id: str | None = None,
        slack_workspace_id: str | None = None,
        whatsapp_number: str | None = None,
        account_id: UUID | None = None,
        preferred_channel: str = "email",
        timezone: str = "UTC",
        notification_preferences: str = "all",
    ) -> HumanContact:
        """
        Create a new human contact.

        Args:
            tenant_id: Tenant identifier
            name: Full name of the contact
            email: Email address
            slack_user_id: Slack user ID
            slack_workspace_id: Slack workspace ID
            whatsapp_number: WhatsApp phone number
            account_id: Optional link to Synkora account
            preferred_channel: Preferred notification channel
            timezone: Contact's timezone
            notification_preferences: Notification level

        Returns:
            Created HumanContact instance
        """
        # Validate at least one contact method is provided
        if not email and not slack_user_id and not whatsapp_number:
            raise ValueError("At least one contact method (email, slack, or whatsapp) is required")

        # Validate preferred channel is available
        if preferred_channel == "slack" and not (slack_user_id and slack_workspace_id):
            raise ValueError("Slack user ID and workspace ID required for Slack as preferred channel")
        if preferred_channel == "whatsapp" and not whatsapp_number:
            raise ValueError("WhatsApp number required for WhatsApp as preferred channel")
        if preferred_channel == "email" and not email:
            raise ValueError("Email required for email as preferred channel")

        contact = HumanContact(
            tenant_id=tenant_id,
            name=name,
            email=email,
            slack_user_id=slack_user_id,
            slack_workspace_id=slack_workspace_id,
            whatsapp_number=whatsapp_number,
            account_id=account_id,
            preferred_channel=preferred_channel,
            timezone=timezone,
            notification_preferences=notification_preferences,
            is_active=True,
        )

        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)

        logger.info(f"Created human contact: {name} (id={contact.id})")
        return contact

    async def get_contact(self, contact_id: UUID) -> HumanContact | None:
        """Get a contact by ID."""
        result = await self.db.execute(select(HumanContact).filter(HumanContact.id == contact_id))
        return result.scalar_one_or_none()

    async def get_contact_by_email(self, tenant_id: UUID, email: str) -> HumanContact | None:
        """Get a contact by email within a tenant."""
        result = await self.db.execute(
            select(HumanContact).filter(and_(HumanContact.tenant_id == tenant_id, HumanContact.email == email))
        )
        return result.scalar_one_or_none()

    async def get_contact_by_slack_id(
        self, tenant_id: UUID, slack_user_id: str, workspace_id: str | None = None
    ) -> HumanContact | None:
        """Get a contact by Slack user ID."""
        stmt = select(HumanContact).filter(
            and_(HumanContact.tenant_id == tenant_id, HumanContact.slack_user_id == slack_user_id)
        )

        if workspace_id:
            stmt = stmt.filter(HumanContact.slack_workspace_id == workspace_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_contacts(
        self, tenant_id: UUID, active_only: bool = True, search: str | None = None
    ) -> list[HumanContact]:
        """
        List contacts for a tenant.

        Args:
            tenant_id: Tenant identifier
            active_only: Only return active contacts
            search: Optional search string for name/email

        Returns:
            List of HumanContact instances
        """
        stmt = select(HumanContact).filter(HumanContact.tenant_id == tenant_id)

        if active_only:
            stmt = stmt.filter(HumanContact.is_active)

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.filter((HumanContact.name.ilike(search_pattern)) | (HumanContact.email.ilike(search_pattern)))

        stmt = stmt.order_by(HumanContact.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_contact(self, contact_id: UUID, tenant_id: UUID, **kwargs) -> HumanContact | None:
        """
        Update a contact.

        Args:
            contact_id: Contact ID to update
            tenant_id: Tenant ID for validation
            **kwargs: Fields to update

        Returns:
            Updated HumanContact or None if not found
        """
        result = await self.db.execute(
            select(HumanContact).filter(and_(HumanContact.id == contact_id, HumanContact.tenant_id == tenant_id))
        )
        contact = result.scalar_one_or_none()

        if not contact:
            logger.warning(f"Contact not found or access denied: {contact_id}")
            return None

        # Update allowed fields
        allowed_fields = {
            "name",
            "email",
            "slack_user_id",
            "slack_workspace_id",
            "whatsapp_number",
            "account_id",
            "preferred_channel",
            "is_active",
            "timezone",
            "notification_preferences",
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(contact, key, value)

        # Validate preferred channel after update
        if contact.preferred_channel == "slack" and not contact.has_slack:
            raise ValueError("Slack configuration incomplete for preferred channel")
        if contact.preferred_channel == "whatsapp" and not contact.has_whatsapp:
            raise ValueError("WhatsApp not configured for preferred channel")
        if contact.preferred_channel == "email" and not contact.has_email:
            raise ValueError("Email not configured for preferred channel")

        await self.db.commit()
        await self.db.refresh(contact)

        logger.info(f"Updated contact: {contact_id}")
        return contact

    async def delete_contact(self, contact_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete a contact.

        Args:
            contact_id: Contact ID to delete
            tenant_id: Tenant ID for validation

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            select(HumanContact).filter(and_(HumanContact.id == contact_id, HumanContact.tenant_id == tenant_id))
        )
        contact = result.scalar_one_or_none()

        if not contact:
            logger.warning(f"Contact not found or access denied: {contact_id}")
            return False

        await self.db.delete(contact)
        await self.db.commit()

        logger.info(f"Deleted contact: {contact_id}")
        return True

    async def deactivate_contact(self, contact_id: UUID, tenant_id: UUID) -> HumanContact | None:
        """
        Deactivate a contact instead of deleting.

        Args:
            contact_id: Contact ID to deactivate
            tenant_id: Tenant ID for validation

        Returns:
            Updated HumanContact or None
        """
        return await self.update_contact(contact_id, tenant_id, is_active=False)

    async def get_contact_for_agent(self, agent_id: UUID) -> HumanContact | None:
        """
        Get the human contact linked to an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Linked HumanContact or None
        """
        from src.models import Agent

        result = await self.db.execute(select(Agent).filter(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent or not agent.human_contact_id:
            return None

        return await self.get_contact(agent.human_contact_id)
