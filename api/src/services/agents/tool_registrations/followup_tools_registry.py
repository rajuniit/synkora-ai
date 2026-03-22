"""
Followup Tools Registry

Registers all followup management tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_followup_tools(registry):
    """
    Register all followup management tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.followup_tools import (
        internal_create_followup_item,
        internal_escalate_followup,
        internal_get_followup_history,
        internal_list_pending_followups,
        internal_mark_followup_complete,
        internal_search_slack_mentions,
        internal_send_followup_message,
        internal_update_followup_priority,
    )

    # Followup tools - create wrappers that inject runtime_context
    async def internal_create_followup_item_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_create_followup_item(
            title=kwargs.get("title"),
            initial_message=kwargs.get("initial_message"),
            source_type=kwargs.get("source_type"),
            source_id=kwargs.get("source_id"),
            assignee=kwargs.get("assignee"),
            mentioned_users=kwargs.get("mentioned_users"),
            mentioned_user_names=kwargs.get("mentioned_user_names"),
            channel_id=kwargs.get("channel_id"),
            channel_name=kwargs.get("channel_name"),
            source_url=kwargs.get("source_url"),
            description=kwargs.get("description"),
            priority=kwargs.get("priority", "medium"),
            followup_frequency_hours=kwargs.get("followup_frequency_hours", 24),
            max_followup_attempts=kwargs.get("max_followup_attempts", 3),
            context=kwargs.get("context"),
            runtime_context=runtime_context,
        )

    async def internal_list_pending_followups_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_list_pending_followups(
            status=kwargs.get("status"),
            priority=kwargs.get("priority"),
            assignee=kwargs.get("assignee"),
            due_soon=kwargs.get("due_soon", False),
            limit=kwargs.get("limit", 50),
            runtime_context=runtime_context,
        )

    async def internal_send_followup_message_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_send_followup_message(
            followup_item_id=kwargs.get("followup_item_id"),
            message=kwargs.get("message"),
            message_channel=kwargs.get("message_channel", "slack_dm"),
            ai_reasoning=kwargs.get("ai_reasoning"),
            ai_tone=kwargs.get("ai_tone", "professional"),
            runtime_context=runtime_context,
        )

    async def internal_mark_followup_complete_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_mark_followup_complete(
            followup_item_id=kwargs.get("followup_item_id"),
            response_text=kwargs.get("response_text"),
            completion_reason=kwargs.get("completion_reason"),
            runtime_context=runtime_context,
        )

    async def internal_get_followup_history_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_followup_history(
            followup_item_id=kwargs.get("followup_item_id"), runtime_context=runtime_context
        )

    async def internal_search_slack_mentions_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_search_slack_mentions(
            keywords=kwargs.get("keywords"),
            channels=kwargs.get("channels"),
            days_back=kwargs.get("days_back", 7),
            runtime_context=runtime_context,
        )

    async def internal_update_followup_priority_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_update_followup_priority(
            followup_item_id=kwargs.get("followup_item_id"),
            priority=kwargs.get("priority"),
            runtime_context=runtime_context,
        )

    async def internal_escalate_followup_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_escalate_followup(
            followup_item_id=kwargs.get("followup_item_id"),
            escalation_targets=kwargs.get("escalation_targets"),
            escalation_reason=kwargs.get("escalation_reason"),
            runtime_context=runtime_context,
        )

    # Register all followup tools
    registry.register_tool(
        name="internal_create_followup_item",
        description="Create a new followup item to track. Use this when you notice a Slack message or email that mentions someone and requires them to take action or respond. This will automatically schedule followup reminders.",
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Brief title for the followup (e.g., 'John to review Q4 budget')",
                },
                "initial_message": {
                    "type": "string",
                    "description": "The original message that triggered the followup",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["slack_message", "slack_thread", "email", "manual"],
                    "description": "Type of source where the followup originated",
                },
                "source_id": {
                    "type": "string",
                    "description": "Unique identifier for the source (Slack message timestamp, email ID, etc.)",
                },
                "assignee": {"type": "string", "description": "Primary person to follow up with (user ID or name)"},
                "mentioned_users": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of mentioned user IDs",
                },
                "mentioned_user_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of mentioned user names",
                },
                "channel_id": {"type": "string", "description": "Slack channel ID or email thread ID"},
                "channel_name": {"type": "string", "description": "Slack channel name or email subject"},
                "source_url": {"type": "string", "description": "Permalink to the original message"},
                "description": {"type": "string", "description": "Additional context about the followup"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level of the followup",
                    "default": "medium",
                },
                "followup_frequency_hours": {
                    "type": "integer",
                    "description": "How often to follow up in hours",
                    "default": 24,
                },
                "max_followup_attempts": {
                    "type": "integer",
                    "description": "Maximum number of followup attempts before escalation",
                    "default": 3,
                },
                "context": {"type": "object", "description": "Additional context data as JSON object"},
            },
            "required": ["title", "initial_message", "source_type", "source_id"],
        },
        function=internal_create_followup_item_wrapper,
    )

    registry.register_tool(
        name="internal_list_pending_followups",
        description="List pending followup items. Use this to see what followups are pending, overdue, or due soon. Great for daily standup summaries or checking what needs attention.",
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled", "escalated"],
                    "description": "Filter by status",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Filter by priority",
                },
                "assignee": {"type": "string", "description": "Filter by assignee name or ID"},
                "due_soon": {
                    "type": "boolean",
                    "description": "If true, only return items due in next 24 hours",
                    "default": False,
                },
                "limit": {"type": "integer", "description": "Maximum number of items to return", "default": 50},
            },
            "required": [],
        },
        function=internal_list_pending_followups_wrapper,
    )

    registry.register_tool(
        name="internal_send_followup_message",
        description="Send a followup message for a specific followup item. The message will be sent via Slack DM or in the original channel thread. Use this to politely remind someone about pending action items.",
        parameters={
            "type": "object",
            "properties": {
                "followup_item_id": {"type": "string", "description": "UUID of the followup item"},
                "message": {"type": "string", "description": "Message to send as followup"},
                "message_channel": {
                    "type": "string",
                    "enum": ["slack_dm", "slack_channel", "email"],
                    "description": "Channel to send through",
                    "default": "slack_dm",
                },
                "ai_reasoning": {"type": "string", "description": "AI's reasoning for sending this followup"},
                "ai_tone": {
                    "type": "string",
                    "enum": ["professional", "friendly", "casual", "urgent"],
                    "description": "Tone to use in the message",
                    "default": "professional",
                },
            },
            "required": ["followup_item_id", "message"],
        },
        function=internal_send_followup_message_wrapper,
    )

    registry.register_tool(
        name="internal_mark_followup_complete",
        description="PERMANENTLY mark a followup as completed and STOP all recurring reminders. Only use this when the user EXPLICITLY asks to STOP, CANCEL, CLOSE, or END the reminder. DO NOT use this when the user simply acknowledges a recurring reminder (e.g., 'yes', 'done', 'ok') - in that case, just respond naturally and let the scheduled reminder continue running.",
        parameters={
            "type": "object",
            "properties": {
                "followup_item_id": {"type": "string", "description": "UUID of the followup item"},
                "response_text": {"type": "string", "description": "Response received that completed the followup"},
                "completion_reason": {
                    "type": "string",
                    "description": "Reason for completion (e.g., 'User requested to stop reminders')",
                },
            },
            "required": ["followup_item_id"],
        },
        function=internal_mark_followup_complete_wrapper,
    )

    registry.register_tool(
        name="internal_get_followup_history",
        description="Get the full history of a followup item including all attempts made. Use this to understand the followup timeline and what has been tried.",
        parameters={
            "type": "object",
            "properties": {"followup_item_id": {"type": "string", "description": "UUID of the followup item"}},
            "required": ["followup_item_id"],
        },
        function=internal_get_followup_history_wrapper,
    )

    registry.register_tool(
        name="internal_search_slack_mentions",
        description="Search for Slack messages that mention specific keywords or people. Use this to automatically detect messages that might need followup.",
        parameters={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for (e.g., ['@john', 'deadline', 'action item'])",
                },
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific channels to search in",
                },
                "days_back": {"type": "integer", "description": "How many days back to search", "default": 7},
            },
            "required": [],
        },
        function=internal_search_slack_mentions_wrapper,
    )

    registry.register_tool(
        name="internal_update_followup_priority",
        description="Update the priority of a followup item. Use this when circumstances change and a followup becomes more or less urgent.",
        parameters={
            "type": "object",
            "properties": {
                "followup_item_id": {"type": "string", "description": "UUID of the followup item"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "New priority level",
                },
            },
            "required": ["followup_item_id", "priority"],
        },
        function=internal_update_followup_priority_wrapper,
    )

    registry.register_tool(
        name="internal_escalate_followup",
        description="Escalate a followup item to specific people or channels when maximum attempts are reached without response. Use this to notify managers or team leads about unresolved items.",
        parameters={
            "type": "object",
            "properties": {
                "followup_item_id": {"type": "string", "description": "UUID of the followup item"},
                "escalation_targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs or email addresses to escalate to",
                },
                "escalation_reason": {"type": "string", "description": "Reason for escalation"},
            },
            "required": ["followup_item_id", "escalation_targets"],
        },
        function=internal_escalate_followup_wrapper,
    )

    logger.info("Registered 8 followup management tools")
