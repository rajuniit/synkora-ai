"""
Human Escalation Service

Service for managing escalations from agents to humans.
Handles creation, notification, and resolution of escalations
using Slack, WhatsApp, and Email notification channels.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    EscalationPriority,
    EscalationStatus,
    HumanContact,
    HumanEscalation,
)

logger = logging.getLogger(__name__)


class HumanEscalationService:
    """Service for managing human escalations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_escalation(
        self,
        tenant_id: UUID,
        project_id: UUID,
        from_agent_id: UUID,
        to_human_id: UUID,
        reason: str,
        subject: str,
        message: str,
        context_summary: str | None = None,
        priority: str = EscalationPriority.MEDIUM.value,
        conversation_id: UUID | None = None,
        expires_in_hours: int | None = 24,
        auto_notify: bool = True,
    ) -> HumanEscalation:
        """
        Create a new escalation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project this escalation belongs to
            from_agent_id: Agent initiating the escalation
            to_human_id: Human contact to notify
            reason: Reason for escalation
            subject: Brief subject line
            message: Detailed message
            context_summary: AI-generated summary of context
            priority: Urgency level
            conversation_id: Optional conversation context
            expires_in_hours: Hours until expiration (None for no expiry)
            auto_notify: Whether to send notification immediately

        Returns:
            Created HumanEscalation instance
        """
        # Validate human contact exists
        result = await self.db.execute(
            select(HumanContact).filter(
                and_(HumanContact.id == to_human_id, HumanContact.tenant_id == tenant_id, HumanContact.is_active)
            )
        )
        human = result.scalar_one_or_none()

        if not human:
            raise ValueError(f"Human contact not found or inactive: {to_human_id}")

        # Determine which channels to use
        notification_channels = {"slack": human.has_slack, "whatsapp": human.has_whatsapp, "email": human.has_email}

        # Calculate expiration
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)

        escalation = HumanEscalation(
            tenant_id=tenant_id,
            project_id=project_id,
            conversation_id=conversation_id,
            from_agent_id=from_agent_id,
            to_human_id=to_human_id,
            reason=reason,
            priority=priority,
            subject=subject,
            message=message,
            context_summary=context_summary,
            status=EscalationStatus.PENDING.value,
            notification_channels=notification_channels,
            expires_at=expires_at,
        )

        self.db.add(escalation)
        await self.db.commit()
        await self.db.refresh(escalation)

        logger.info(f"Created escalation: {escalation.id} (reason={reason}, priority={priority})")

        # Send notification if auto_notify is enabled
        if auto_notify:
            await self.notify_human(escalation.id, tenant_id)

        return escalation

    async def notify_human(self, escalation_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """
        Send notification to the human contact.

        Uses the human's preferred channel, falling back to others if needed.

        Args:
            escalation_id: Escalation ID
            tenant_id: Tenant ID for validation

        Returns:
            Dictionary with notification results per channel
        """
        result = await self.db.execute(
            select(HumanEscalation).filter(
                and_(HumanEscalation.id == escalation_id, HumanEscalation.tenant_id == tenant_id)
            )
        )
        escalation = result.scalar_one_or_none()

        if not escalation:
            return {"success": False, "error": "Escalation not found"}

        human = escalation.to_human
        if not human:
            return {"success": False, "error": "Human contact not found"}

        results = {"success": False, "channels": {}}

        notification_metadata = {}

        # Get project and agent info for the notification
        project = escalation.project
        agent = escalation.from_agent

        project_name = project.name if project else "Unknown Project"
        agent_name = agent.agent_name if agent else "AI Agent"

        # Format the notification message
        notification_message = self._format_notification_message(
            escalation=escalation, project_name=project_name, agent_name=agent_name
        )

        # Try preferred channel first, then others
        channels_to_try = [human.preferred_channel]
        for channel in ["slack", "email", "whatsapp"]:
            if channel not in channels_to_try:
                channels_to_try.append(channel)

        for channel in channels_to_try:
            if not escalation.notification_channels.get(channel):
                continue

            try:
                if channel == "slack" and human.has_slack:
                    result = await self._send_slack_notification(
                        human=human,
                        subject=escalation.subject,
                        message=notification_message,
                        priority=escalation.priority,
                        escalation_id=escalation_id,
                    )
                    results["channels"]["slack"] = result
                    if result.get("success"):
                        notification_metadata["slack_ts"] = result.get("ts")
                        results["success"] = True

                elif channel == "email" and human.has_email:
                    result = await self._send_email_notification(
                        human=human,
                        subject=f"[{escalation.priority.upper()}] {escalation.subject}",
                        message=notification_message,
                        project_name=project_name,
                        agent_name=agent_name,
                        escalation=escalation,
                    )
                    results["channels"]["email"] = result
                    if result.get("success"):
                        results["success"] = True

                elif channel == "whatsapp" and human.has_whatsapp:
                    result = await self._send_whatsapp_notification(
                        human=human, message=f"🚨 {escalation.subject}\n\n{notification_message}"
                    )
                    results["channels"]["whatsapp"] = result
                    if result.get("success"):
                        results["success"] = True

            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results["channels"][channel] = {"success": False, "error": str(e)}

        # Update escalation status
        if results["success"]:
            escalation.status = EscalationStatus.NOTIFIED.value
            escalation.notification_sent_at = datetime.now(UTC)
            escalation.notification_metadata = notification_metadata

            await self.db.commit()
            await self.db.refresh(escalation)

        return results

    def _format_notification_message(self, escalation: HumanEscalation, project_name: str, agent_name: str) -> str:
        """Format the notification message content."""
        priority_emoji = {"low": "📋", "medium": "⚠️", "high": "🔔", "urgent": "🚨"}.get(escalation.priority, "📋")

        reason_label = {
            "uncertainty": "Uncertain about decision",
            "approval_needed": "Approval needed",
            "complex_decision": "Complex decision required",
            "blocker": "Blocker encountered",
            "review_required": "Review required",
            "customer_request": "Customer requested human",
            "security_concern": "Security concern",
            "budget_approval": "Budget approval needed",
        }.get(escalation.reason, escalation.reason)

        message = f"""{priority_emoji} **Escalation from {agent_name}**

**Project:** {project_name}
**Reason:** {reason_label}
**Priority:** {escalation.priority.upper()}

**Message:**
{escalation.message}
"""

        if escalation.context_summary:
            message += f"""
**Context Summary:**
{escalation.context_summary}
"""

        return message

    async def _send_slack_notification(
        self, human: HumanContact, subject: str, message: str, priority: str, escalation_id: UUID
    ) -> dict[str, Any]:
        """Send notification via Slack DM."""
        try:
            # Use internal_slack_send_dm with the human's slack_user_id
            # We need to find a connected Slack bot for this workspace
            from src.models import SlackBot
            from src.services.agents.internal_tools.slack_tools import internal_slack_send_dm

            result = await self.db.execute(
                select(SlackBot).filter(
                    and_(SlackBot.workspace_id == human.slack_workspace_id, SlackBot.connection_status == "connected")
                )
            )
            slack_bot = result.scalar_one_or_none()

            if not slack_bot:
                return {"success": False, "error": "No connected Slack bot for workspace"}

            # Build runtime context for the Slack tool
            runtime_context = {"agent_id": str(slack_bot.agent_id), "db_session": self.db}

            result = await internal_slack_send_dm(
                user_id=human.slack_user_id, text=f"**{subject}**\n\n{message}", runtime_context=runtime_context
            )

            return result

        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return {"success": False, "error": str(e)}

    async def _send_email_notification(
        self,
        human: HumanContact,
        subject: str,
        message: str,
        project_name: str,
        agent_name: str,
        escalation: HumanEscalation,
    ) -> dict[str, Any]:
        """Send notification via Email."""
        try:
            from src.services.integrations.email_service import EmailService

            email_service = EmailService(self.db)

            # Create HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .content {{ background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                    .priority-urgent {{ background-color: #dc2626; }}
                    .priority-high {{ background-color: #f97316; }}
                    .priority-medium {{ background-color: #f59e0b; }}
                    .priority-low {{ background-color: #10b981; }}
                    .meta {{ background-color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }}
                    .message-box {{ background-color: white; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; }}
                    .footer {{ margin-top: 20px; font-size: 12px; color: #6b7280; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header priority-{escalation.priority}">
                        <h2 style="margin: 0;">🤖 Agent Escalation</h2>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">From {agent_name} • {project_name}</p>
                    </div>
                    <div class="content">
                        <div class="meta">
                            <strong>Reason:</strong> {escalation.reason.replace("_", " ").title()}<br>
                            <strong>Priority:</strong> {escalation.priority.upper()}<br>
                            <strong>Project:</strong> {project_name}
                        </div>
                        <div class="message-box">
                            <h3 style="margin-top: 0;">Message</h3>
                            <p>{escalation.message.replace(chr(10), "<br>")}</p>
                        </div>
                        {f'<div class="message-box" style="margin-top: 15px; border-left-color: #6b7280;"><h4 style="margin-top: 0;">Context Summary</h4><p>{escalation.context_summary}</p></div>' if escalation.context_summary else ""}
                    </div>
                    <div class="footer">
                        <p>This escalation was created automatically by Synkora.</p>
                        <p>Escalation ID: {escalation.id}</p>
                    </div>
                </div>
            </body>
            </html>
            """

            result = email_service.send_email(
                to_email=human.email,
                subject=subject,
                html_content=html_content,
                text_content=message,
                tenant_id=escalation.tenant_id,
            )

            return result

        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return {"success": False, "error": str(e)}

    async def _send_whatsapp_notification(self, human: HumanContact, message: str) -> dict[str, Any]:
        """Send notification via WhatsApp."""
        try:
            from src.models import WhatsAppBot

            # Find an active WhatsApp bot
            result = await self.db.execute(
                select(WhatsAppBot).filter(and_(WhatsAppBot.tenant_id == human.tenant_id, WhatsAppBot.is_active))
            )
            whatsapp_bot = result.scalar_one_or_none()

            if not whatsapp_bot:
                return {"success": False, "error": "No active WhatsApp bot configured"}

            from src.services.whatsapp.whatsapp_webhook_service import WhatsAppWebhookService

            whatsapp_service = WhatsAppWebhookService(self.db)
            await whatsapp_service._send_message(bot=whatsapp_bot, to_number=human.whatsapp_number, text=message)

            return {"success": True}

        except Exception as e:
            logger.error(f"WhatsApp notification failed: {e}")
            return {"success": False, "error": str(e)}

    async def resolve_escalation(
        self, escalation_id: UUID, tenant_id: UUID, response: str, resolution_notes: str | None = None
    ) -> HumanEscalation | None:
        """
        Resolve an escalation with human response.

        Args:
            escalation_id: Escalation ID
            tenant_id: Tenant ID for validation
            response: Human's response
            resolution_notes: Additional notes

        Returns:
            Updated HumanEscalation or None
        """
        result = await self.db.execute(
            select(HumanEscalation).filter(
                and_(HumanEscalation.id == escalation_id, HumanEscalation.tenant_id == tenant_id)
            )
        )
        escalation = result.scalar_one_or_none()

        if not escalation:
            return None

        escalation.status = EscalationStatus.RESOLVED.value
        escalation.human_response = response
        escalation.resolution_notes = resolution_notes
        escalation.resolved_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(escalation)

        logger.info(f"Resolved escalation: {escalation_id}")
        return escalation

    async def get_escalation(self, escalation_id: UUID) -> HumanEscalation | None:
        """Get an escalation by ID."""
        result = await self.db.execute(select(HumanEscalation).filter(HumanEscalation.id == escalation_id))
        return result.scalar_one_or_none()

    async def list_escalations(
        self,
        tenant_id: UUID,
        status: str | None = None,
        project_id: UUID | None = None,
        human_id: UUID | None = None,
        agent_id: UUID | None = None,
        include_expired: bool = False,
    ) -> list[HumanEscalation]:
        """
        List escalations with filters.

        Args:
            tenant_id: Tenant identifier
            status: Optional status filter
            project_id: Optional project filter
            human_id: Optional human contact filter
            agent_id: Optional agent filter
            include_expired: Whether to include expired escalations

        Returns:
            List of HumanEscalation instances
        """
        stmt = select(HumanEscalation).filter(HumanEscalation.tenant_id == tenant_id)

        if status:
            stmt = stmt.filter(HumanEscalation.status == status)

        if project_id:
            stmt = stmt.filter(HumanEscalation.project_id == project_id)

        if human_id:
            stmt = stmt.filter(HumanEscalation.to_human_id == human_id)

        if agent_id:
            stmt = stmt.filter(HumanEscalation.from_agent_id == agent_id)

        if not include_expired:
            stmt = stmt.filter(
                or_(HumanEscalation.expires_at.is_(None), HumanEscalation.expires_at > datetime.now(UTC))
            )

        stmt = stmt.order_by(HumanEscalation.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_escalations(self, human_id: UUID) -> list[HumanEscalation]:
        """
        Get pending escalations for a human contact.

        Args:
            human_id: Human contact ID

        Returns:
            List of pending HumanEscalation instances
        """
        stmt = (
            select(HumanEscalation)
            .filter(
                and_(
                    HumanEscalation.to_human_id == human_id,
                    HumanEscalation.status.in_(
                        [
                            EscalationStatus.PENDING.value,
                            EscalationStatus.NOTIFIED.value,
                            EscalationStatus.IN_PROGRESS.value,
                        ]
                    ),
                    or_(HumanEscalation.expires_at.is_(None), HumanEscalation.expires_at > datetime.now(UTC)),
                )
            )
            .order_by(
                # Urgent first, then by created_at
                HumanEscalation.priority.desc(),
                HumanEscalation.created_at.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_in_progress(self, escalation_id: UUID, tenant_id: UUID) -> HumanEscalation | None:
        """Mark an escalation as in progress."""
        result = await self.db.execute(
            select(HumanEscalation).filter(
                and_(HumanEscalation.id == escalation_id, HumanEscalation.tenant_id == tenant_id)
            )
        )
        escalation = result.scalar_one_or_none()

        if not escalation:
            return None

        escalation.status = EscalationStatus.IN_PROGRESS.value
        await self.db.commit()
        await self.db.refresh(escalation)

        return escalation

    async def expire_old_escalations(self, tenant_id: UUID | None = None) -> int:
        """
        Mark expired escalations.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            Number of escalations marked as expired
        """
        stmt = select(HumanEscalation).filter(
            and_(
                HumanEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.NOTIFIED.value]),
                HumanEscalation.expires_at.is_not(None),
                HumanEscalation.expires_at < datetime.now(UTC),
            )
        )

        if tenant_id:
            stmt = stmt.filter(HumanEscalation.tenant_id == tenant_id)

        result = await self.db.execute(stmt)
        escalations = result.scalars().all()

        count = 0
        for escalation in escalations:
            escalation.status = EscalationStatus.EXPIRED.value
            count += 1

        if count > 0:
            await self.db.commit()
            logger.info(f"Expired {count} escalations")

        return count
