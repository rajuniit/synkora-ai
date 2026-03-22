"""
Slack Tools Registry

Registers all Slack-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_slack_tools(registry):
    """
    Register all Slack tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.slack_tools import (
        internal_slack_add_reaction,
        internal_slack_join_channel,
        internal_slack_list_channels,
        internal_slack_read_channel_messages,
        internal_slack_read_thread,
        internal_slack_search_messages,
        internal_slack_send_dm,
        internal_slack_send_message,
    )

    # Slack tools - create wrappers that inject runtime_context
    async def internal_slack_list_channels_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_list_channels(
            include_private=kwargs.get("include_private", False), runtime_context=runtime_context, config=config
        )

    async def internal_slack_read_channel_messages_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_read_channel_messages(
            channel_id=kwargs.get("channel_id"),
            limit=kwargs.get("limit", 50),
            hours_ago=kwargs.get("hours_ago"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_slack_read_thread_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_read_thread(
            channel_id=kwargs.get("channel_id"),
            thread_ts=kwargs.get("thread_ts"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_slack_send_message_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_send_message(
            channel_id=kwargs.get("channel_id"),
            text=kwargs.get("text"),
            thread_ts=kwargs.get("thread_ts"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_slack_join_channel_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_join_channel(
            channel_id=kwargs.get("channel_id"), runtime_context=runtime_context, config=config
        )

    async def internal_slack_search_messages_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_search_messages(
            query=kwargs.get("query"), count=kwargs.get("count", 20), runtime_context=runtime_context, config=config
        )

    async def internal_slack_add_reaction_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_add_reaction(
            channel_id=kwargs.get("channel_id"),
            timestamp=kwargs.get("timestamp"),
            emoji=kwargs.get("emoji"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_slack_send_dm_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_slack_send_dm(
            user_id=kwargs.get("user_id"), text=kwargs.get("text"), runtime_context=runtime_context, config=config
        )

    # Register all Slack tools
    registry.register_tool(
        name="internal_slack_list_channels",
        description="List all Slack channels you can see. Use this to discover channels you might want to monitor or join.",
        parameters={
            "type": "object",
            "properties": {
                "include_private": {
                    "type": "boolean",
                    "description": "Whether to include private channels in the list",
                    "default": False,
                }
            },
            "required": [],
        },
        function=internal_slack_list_channels_wrapper,
    )

    registry.register_tool(
        name="internal_slack_read_channel_messages",
        description="Read recent messages from a Slack channel to understand what's being discussed. Use this to monitor channels and decide if you should participate. The agent should use this proactively to stay informed about team discussions.",
        parameters={
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Slack channel ID (e.g., 'C1234567890')"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to retrieve (default 50, max 1000)",
                    "default": 50,
                },
                "hours_ago": {"type": "integer", "description": "Only get messages from the last N hours (optional)"},
            },
            "required": ["channel_id"],
        },
        function=internal_slack_read_channel_messages_wrapper,
    )

    registry.register_tool(
        name="internal_slack_read_thread",
        description="Read all messages in a specific thread. Use this when you see a thread with replies and want to understand the full conversation context before responding.",
        parameters={
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Slack channel ID"},
                "thread_ts": {"type": "string", "description": "Thread timestamp (the parent message timestamp)"},
            },
            "required": ["channel_id", "thread_ts"],
        },
        function=internal_slack_read_thread_wrapper,
    )

    registry.register_tool(
        name="internal_slack_send_message",
        description="Send a message to a Slack channel or thread. Use this when you've decided that responding would be valuable based on the context. Consider carefully whether your response adds value to the conversation. Be human-like in your communication style.",
        parameters={
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Slack channel ID"},
                "text": {"type": "string", "description": "Message text to send"},
                "thread_ts": {
                    "type": "string",
                    "description": "Optional thread timestamp to reply in thread (recommended to keep conversations organized)",
                },
            },
            "required": ["channel_id", "text"],
        },
        function=internal_slack_send_message_wrapper,
    )

    registry.register_tool(
        name="internal_slack_join_channel",
        description="Join a Slack channel. Use this when you discover a channel that's relevant to your role and you want to monitor or participate in it.",
        parameters={
            "type": "object",
            "properties": {"channel_id": {"type": "string", "description": "Slack channel ID to join"}},
            "required": ["channel_id"],
        },
        function=internal_slack_join_channel_wrapper,
    )

    registry.register_tool(
        name="internal_slack_search_messages",
        description="Search for messages across all channels. Use this to find discussions about specific topics, features, or issues that might be relevant to your work.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports Slack search operators like 'from:@user', 'in:#channel', etc.)",
                },
                "count": {"type": "integer", "description": "Number of results to return (max 100)", "default": 20},
            },
            "required": ["query"],
        },
        function=internal_slack_search_messages_wrapper,
    )

    registry.register_tool(
        name="internal_slack_add_reaction",
        description="Add an emoji reaction to a message. Use this for lightweight acknowledgment or to show agreement without sending a message. This is a human-like way to participate without being verbose.",
        parameters={
            "type": "object",
            "properties": {
                "channel_id": {"type": "string", "description": "Slack channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp"},
                "emoji": {
                    "type": "string",
                    "description": "Emoji name without colons (e.g., 'thumbsup', 'eyes', 'white_check_mark')",
                },
            },
            "required": ["channel_id", "timestamp", "emoji"],
        },
        function=internal_slack_add_reaction_wrapper,
    )

    registry.register_tool(
        name="internal_slack_send_dm",
        description="Send a direct message (DM) to a Slack user. Use this to send private messages directly to individual users. Provide the user's Slack ID (e.g., 'U1234567890') and the message text.",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Slack user ID (e.g., 'U1234567890'). This is the unique identifier for the user, not their display name.",
                },
                "text": {"type": "string", "description": "Message text to send to the user"},
            },
            "required": ["user_id", "text"],
        },
        function=internal_slack_send_dm_wrapper,
    )

    logger.info("Registered 8 Slack tools")
