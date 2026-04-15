"""Followup Tools for Autonomous Agent Interaction.

These tools allow agents to create, track, and manage followup items,
particularly for Slack messages and email threads.
"""

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select

from src.core.database import get_async_db
from src.models.followup import FollowupHistory, FollowupItem, FollowupStatus
from src.services.agents.internal_tools.slack_tools import (
    internal_slack_search_messages,
    internal_slack_send_message,
)

logger = logging.getLogger(__name__)


def _ensure_user_id_format(text: str | None) -> str | None:
    """
    Ensure all user IDs in text are properly formatted with @ prefix.

    Converts patterns like:
    - "user U07V0LB1CDD" → "@U07V0LB1CDD"
    - "CC'd user U07V0LB1CDD" → "CC: @U07V0LB1CDD"
    - "U07V0LB1CDD for visibility" → "@U07V0LB1CDD for visibility"
    - "CC: U07V0LB1CDD" → "CC: @U07V0LB1CDD"

    Args:
        text: Text that may contain user IDs

    Returns:
        Text with properly formatted user IDs
    """
    if not text:
        return text

    # Pattern 1: "user U..." → "@U..."
    text = re.sub(r"\buser\s+(U[A-Z0-9]+)", r"@\1", text, flags=re.IGNORECASE)

    # Pattern 2: "CC'd user U..." → "CC: @U..."
    text = re.sub(r"\bCC\'d\s+user\s+(U[A-Z0-9]+)", r"CC: @\1", text, flags=re.IGNORECASE)

    # Pattern 3: Standalone user IDs without @ → add @
    # Only match if not already preceded by @
    text = re.sub(r"(?<!@)(U[A-Z0-9]{10})", r"@\1", text)

    # Pattern 4: Clean up multiple @ symbols (@@U... → @U...)
    text = re.sub(r"@+", "@", text)

    return text


async def internal_create_followup_item(
    title: str,
    initial_message: str,
    source_type: str,
    source_id: str,
    assignee: str | None = None,
    mentioned_users: list[str] | None = None,
    mentioned_user_names: list[str] | None = None,
    channel_id: str | None = None,
    channel_name: str | None = None,
    source_url: str | None = None,
    description: str | None = None,
    priority: str = "medium",
    followup_frequency_hours: int = 24,
    max_followup_attempts: int = 3,
    context: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a new followup item to track.

    Args:
        title: Brief title for the followup item
        initial_message: The original message that triggered the followup
        source_type: Type of source (slack_message, slack_thread, email, manual)
        source_id: Unique identifier for the source (message timestamp, email ID, etc.)
        assignee: Primary person to follow up with
        mentioned_users: List of mentioned user IDs
        mentioned_user_names: List of mentioned user names
        channel_id: Slack channel ID or email thread ID
        channel_name: Slack channel name or email subject
        source_url: Permalink to the original message
        description: Additional context about the followup
        priority: Priority level (low, medium, high, urgent)
        followup_frequency_hours: How often to follow up (in hours)
        max_followup_attempts: Maximum number of followup attempts
        context: Additional context data
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with followup item details
    """
    try:
        # Convert followup_frequency_hours to float (LLM may pass as string like "24" or "24h")
        try:
            followup_frequency_hours = float(str(followup_frequency_hours).rstrip("hHmMsS"))
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid followup_frequency_hours: '{followup_frequency_hours}'. Must be a number.",
            }
        try:
            max_followup_attempts = int(str(max_followup_attempts).split(".")[0])
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid max_followup_attempts: '{max_followup_attempts}'. Must be an integer.",
            }

        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
                tenant_id = runtime_context.get("tenant_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
                tenant_id = getattr(runtime_context, "tenant_id", None)
        else:
            agent_id = None
            tenant_id = None

        if not agent_id or not tenant_id:
            return {"success": False, "error": "Missing agent_id or tenant_id in runtime context"}

        async for db in get_async_db():
            # Calculate next followup date
            next_followup_at = datetime.now(UTC) + timedelta(hours=followup_frequency_hours)

            # Ensure user IDs in description are properly formatted with @ prefix
            formatted_description = _ensure_user_id_format(description)

            # Log if description was reformatted
            if formatted_description != description:
                logger.info(f"Reformatted description from: {description}")
                logger.info(f"Reformatted description to: {formatted_description}")

            # Create followup item
            followup_item = FollowupItem(
                tenant_id=uuid.UUID(str(tenant_id)),
                agent_id=uuid.UUID(str(agent_id)),
                source_type=source_type,
                source_id=source_id,
                source_url=source_url,
                channel_id=channel_id,
                channel_name=channel_name,
                title=title,
                description=formatted_description,
                initial_message=initial_message,
                context=context,
                mentioned_users=mentioned_users,
                mentioned_user_names=mentioned_user_names,
                assignee=assignee,
                status=FollowupStatus.PENDING.value,
                priority=priority,
                next_followup_at=next_followup_at,
                followup_frequency_hours=followup_frequency_hours,
                max_followup_attempts=max_followup_attempts,
                current_attempt_count=0,
            )

            db.add(followup_item)
            await db.commit()
            await db.refresh(followup_item)

            # Auto-create scheduled task for followup reminders
            from src.models.scheduled_task import ScheduledTask

            scheduled_task = ScheduledTask(
                tenant_id=followup_item.tenant_id,
                name=f"Followup Reminder: {title}",
                description=f"Automated followup reminder for: {title}",
                task_type="followup_reminder",
                schedule_type="interval",
                interval_seconds=followup_frequency_hours * 3600,  # Convert hours to seconds
                config={
                    "followup_item_id": str(followup_item.id),
                    "agent_id": str(followup_item.agent_id),
                    "action": "send_reminder",
                },
                is_active=True,
                next_run_at=next_followup_at,
                # Prevent immediate fire on first Beat check — first reminder
                # fires after the full interval (aligned with next_followup_at).
                last_run_at=datetime.now(UTC),
                created_by=followup_item.tenant_id,  # Using tenant_id as created_by for system tasks
            )
            db.add(scheduled_task)
            await db.commit()
            await db.refresh(scheduled_task)

            logger.info(f"✅ Created followup item {followup_item.id} with scheduled task {scheduled_task.id}")

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "scheduled_task_id": str(scheduled_task.id),
                "message": f"Followup item created successfully: {title}",
            }

    except Exception as e:
        logger.warning(f"Error creating followup item: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_list_pending_followups(
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    due_soon: bool = False,
    limit: int = 50,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    List pending followup items for the agent.

    Args:
        status: Filter by status (pending, in_progress, completed, cancelled, escalated)
        priority: Filter by priority (low, medium, high, urgent)
        assignee: Filter by assignee name or ID
        due_soon: If true, only return items due in next 24 hours
        limit: Maximum number of items to return
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with list of followup items
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            stmt = select(FollowupItem).filter(FollowupItem.agent_id == uuid.UUID(str(agent_id)))

            # Apply filters
            if status:
                stmt = stmt.filter(FollowupItem.status == status)
            else:
                # Default to non-completed items
                stmt = stmt.filter(
                    FollowupItem.status.in_([FollowupStatus.PENDING.value, FollowupStatus.IN_PROGRESS.value])
                )

            if priority:
                stmt = stmt.filter(FollowupItem.priority == priority)

            if assignee:
                stmt = stmt.filter(
                    or_(FollowupItem.assignee == assignee, FollowupItem.mentioned_users.contains([assignee]))
                )

            if due_soon:
                now = datetime.now(UTC)
                tomorrow = now + timedelta(hours=24)
                stmt = stmt.filter(
                    and_(FollowupItem.next_followup_at <= tomorrow, FollowupItem.next_followup_at >= now)
                )

            # Order by next followup date
            stmt = stmt.order_by(FollowupItem.next_followup_at.asc())
            stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            items = list(result.scalars().all())

            return {"success": True, "followup_items": [item.to_dict() for item in items], "total": len(items)}

    except Exception as e:
        logger.warning(f"Error listing followup items: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_send_followup_message(
    followup_item_id: str,
    message: str,
    message_channel: str = "slack_dm",
    ai_reasoning: str | None = None,
    ai_tone: str = "professional",
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Send a followup message for a specific followup item.

    Args:
        followup_item_id: UUID of the followup item
        message: Message to send
        message_channel: Channel to send through (slack_dm, slack_channel, email)
        ai_reasoning: AI's reasoning for sending this followup
        ai_tone: Tone used in the message
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with send status
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            # Get followup item
            result = await db.execute(
                select(FollowupItem).filter(
                    FollowupItem.id == uuid.UUID(followup_item_id), FollowupItem.agent_id == uuid.UUID(str(agent_id))
                )
            )
            followup_item = result.scalar_one_or_none()

            if not followup_item:
                return {"success": False, "error": "Followup item not found"}

            # Send message via appropriate channel
            send_result = None

            if message_channel in ["slack_dm", "slack_channel"]:
                # Send via Slack
                if not followup_item.channel_id:
                    return {"success": False, "error": "No channel ID for Slack message"}

                # For DM, we'd typically need the user's DM channel ID
                # For simplicity, sending to the original channel
                send_result = await internal_slack_send_message(
                    channel_id=followup_item.channel_id,
                    text=message,
                    thread_ts=followup_item.source_id if message_channel == "slack_channel" else None,
                    runtime_context=runtime_context,
                )

                if send_result.get("success"):
                    send_result.get("message_ts")

            # Update followup item
            followup_item.current_attempt_count += 1
            followup_item.status = FollowupStatus.IN_PROGRESS.value
            followup_item.last_followup_at = datetime.now(UTC)

            # Calculate next followup date
            if followup_item.current_attempt_count < followup_item.max_followup_attempts:
                followup_item.next_followup_at = datetime.now(UTC) + timedelta(
                    hours=followup_item.followup_frequency_hours
                )
            else:
                # Max attempts reached, mark for escalation
                followup_item.status = FollowupStatus.ESCALATED.value
                followup_item.escalated = True
                followup_item.escalated_at = datetime.now(UTC)
                followup_item.next_followup_at = None

            # Create history record
            history = FollowupHistory(
                followup_item_id=followup_item.id,
                attempt_number=followup_item.current_attempt_count,
                sent_at=datetime.now(UTC),
                message_sent=message,
                message_channel=message_channel,
                ai_reasoning=ai_reasoning,
                ai_tone=ai_tone,
            )

            db.add(history)
            await db.commit()

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "history": history.to_dict(),
                "send_result": send_result,
                "message": f"Followup message sent (attempt {followup_item.current_attempt_count}/{followup_item.max_followup_attempts})",
            }

    except Exception as e:
        logger.warning(f"Error sending followup message: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_mark_followup_complete(
    followup_item_id: str,
    response_text: str | None = None,
    completion_reason: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    PERMANENTLY mark a followup item as completed and STOP all recurring reminders.

    Only use this when the user EXPLICITLY asks to STOP, CANCEL, CLOSE, or END the reminder.
    DO NOT use this when the user simply acknowledges a recurring reminder - in that case,
    just respond naturally and let the scheduled reminder continue running.

    Args:
        followup_item_id: UUID of the followup item
        response_text: Response received that completed the followup
        completion_reason: Reason for completion
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with completion status
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            result = await db.execute(
                select(FollowupItem).filter(
                    FollowupItem.id == uuid.UUID(followup_item_id), FollowupItem.agent_id == uuid.UUID(str(agent_id))
                )
            )
            followup_item = result.scalar_one_or_none()

            if not followup_item:
                return {"success": False, "error": "Followup item not found"}

            # Mark as completed
            followup_item.status = FollowupStatus.COMPLETED.value
            followup_item.response_text = response_text
            followup_item.completed_at = datetime.now(UTC)
            followup_item.next_followup_at = None

            # Also deactivate the associated scheduled task
            from src.models.scheduled_task import ScheduledTask

            result = await db.execute(
                select(ScheduledTask).filter(
                    ScheduledTask.task_type == "followup_reminder",
                    ScheduledTask.config["followup_item_id"].as_string() == str(followup_item.id),
                )
            )
            scheduled_task = result.scalar_one_or_none()

            if scheduled_task:
                scheduled_task.is_active = False
                logger.info(f"Deactivated scheduled task {scheduled_task.id} for completed followup {followup_item.id}")

            await db.commit()

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "message": f"✅ Followup '{followup_item.title}' marked as completed and recurring reminder stopped.",
            }

    except Exception as e:
        logger.warning(f"Error marking followup complete: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_get_followup_history(
    followup_item_id: str, runtime_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get the full history of a followup item.

    Args:
        followup_item_id: UUID of the followup item
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with followup history
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            result = await db.execute(
                select(FollowupItem).filter(
                    FollowupItem.id == uuid.UUID(followup_item_id), FollowupItem.agent_id == uuid.UUID(str(agent_id))
                )
            )
            followup_item = result.scalar_one_or_none()

            if not followup_item:
                return {"success": False, "error": "Followup item not found"}

            result = await db.execute(
                select(FollowupHistory)
                .filter(FollowupHistory.followup_item_id == followup_item.id)
                .order_by(FollowupHistory.sent_at.desc())
            )
            history = list(result.scalars().all())

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "history": [h.to_dict() for h in history],
                "total_attempts": len(history),
            }

    except Exception as e:
        logger.warning(f"Error getting followup history: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_search_slack_mentions(
    keywords: list[str] | None = None,
    channels: list[str] | None = None,
    days_back: int = 7,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Search for Slack messages that mention specific keywords or people.
    Useful for automatically detecting items that need followup.

    Args:
        keywords: Keywords to search for (e.g., ["@john", "deadline", "action item"])
        channels: Specific channels to search in
        days_back: How many days back to search
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with search results
    """
    try:
        # Use existing Slack search functionality
        query_parts = []

        if keywords:
            query_parts.extend(keywords)

        if channels:
            for channel in channels:
                query_parts.append(f"in:{channel}")

        # Add date filter
        query = " ".join(query_parts)

        # Search using internal Slack tools
        results = await internal_slack_search_messages(query=query, count=100, runtime_context=runtime_context)

        return results

    except Exception as e:
        logger.warning(f"Error searching Slack mentions: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_update_followup_priority(
    followup_item_id: str, priority: str, runtime_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Update the priority of a followup item.

    Args:
        followup_item_id: UUID of the followup item
        priority: New priority (low, medium, high, urgent)
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with update status
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            result = await db.execute(
                select(FollowupItem).filter(
                    FollowupItem.id == uuid.UUID(followup_item_id), FollowupItem.agent_id == uuid.UUID(str(agent_id))
                )
            )
            followup_item = result.scalar_one_or_none()

            if not followup_item:
                return {"success": False, "error": "Followup item not found"}

            followup_item.priority = priority
            await db.commit()

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "message": f"Priority updated to {priority}",
            }

    except Exception as e:
        logger.warning(f"Error updating followup priority: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_escalate_followup(
    followup_item_id: str,
    escalation_targets: list[str],
    escalation_reason: str | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Escalate a followup item to specific people or channels.

    Args:
        followup_item_id: UUID of the followup item
        escalation_targets: List of user IDs or email addresses to escalate to
        escalation_reason: Reason for escalation
        runtime_context: Runtime context from agent execution

    Returns:
        Dictionary with escalation status
    """
    try:
        # Handle both dict and RuntimeContext object
        if runtime_context:
            if isinstance(runtime_context, dict):
                agent_id = runtime_context.get("agent_id")
            else:
                agent_id = getattr(runtime_context, "agent_id", None)
        else:
            agent_id = None

        if not agent_id:
            return {"success": False, "error": "Missing agent_id in runtime context"}

        async for db in get_async_db():
            result = await db.execute(
                select(FollowupItem).filter(
                    FollowupItem.id == uuid.UUID(followup_item_id), FollowupItem.agent_id == uuid.UUID(str(agent_id))
                )
            )
            followup_item = result.scalar_one_or_none()

            if not followup_item:
                return {"success": False, "error": "Followup item not found"}

            # Mark as escalated
            followup_item.status = FollowupStatus.ESCALATED.value
            followup_item.escalated = True
            followup_item.escalated_at = datetime.now(UTC)
            followup_item.escalated_to = escalation_targets

            await db.commit()

            # Create history record
            history = FollowupHistory(
                followup_item_id=followup_item.id,
                attempt_number=followup_item.current_attempt_count + 1,
                sent_at=datetime.now(UTC),
                message_sent=f"Escalated to: {', '.join(escalation_targets)}. Reason: {escalation_reason or 'No response after maximum attempts'}",
                message_channel="escalation",
                ai_reasoning=escalation_reason,
            )

            db.add(history)
            await db.commit()

            return {
                "success": True,
                "followup_item": followup_item.to_dict(),
                "escalation_targets": escalation_targets,
                "message": f"Followup escalated to {len(escalation_targets)} target(s)",
            }

    except Exception as e:
        logger.warning(f"Error escalating followup: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
