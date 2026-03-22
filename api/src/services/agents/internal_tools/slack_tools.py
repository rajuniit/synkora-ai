"""Slack Tools for Autonomous Agent Interaction.

These tools allow agents to interact with Slack channels autonomously,
reading messages, understanding context, and deciding when to respond.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select

from src.core.database import get_async_db
from src.models.slack_bot import SlackBot
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


async def _get_slack_client(runtime_context: dict[str, Any], config: dict[str, Any] = None) -> AsyncWebClient | None:
    """
    Get Slack client using OAuth app or legacy Slack bot.

    Tries OAuth app first (via credential_resolver), then falls back to legacy Slack bot.

    Args:
        runtime_context: Runtime context with agent_id and db_session
        config: Config dict that may contain _tool_name from adk_tools
    """
    try:
        # Extract agent_id first
        if isinstance(runtime_context, dict):
            agent_id = runtime_context.get("agent_id")
        else:
            agent_id = getattr(runtime_context, "agent_id", None)

        if not agent_id:
            logger.error("No agent_id in runtime_context")
            return None

        # Try using credential resolver for OAuth app (preferred method)
        # RuntimeContext doesn't have credential_resolver as attribute, we need to create one
        try:
            from src.services.agents.credential_resolver import CredentialResolver

            # Extract tool_name from config (added by adk_tools.py)
            tool_name = None
            if config:
                tool_name = config.get("_tool_name")

            if not tool_name:
                logger.warning("⚠️ No _tool_name in config, using fallback 'slack'")
                tool_name = "slack"

            logger.info(f"🔍 [Slack Tools] Looking up OAuth for tool_name='{tool_name}'")

            # Create credential resolver with runtime_context
            resolver = CredentialResolver(runtime_context)
            token = await resolver.get_slack_token(tool_name)

            if token:
                logger.info(f"✅ Using Slack OAuth token for agent {agent_id}")
                return AsyncWebClient(token=token)
            else:
                logger.info("No Slack OAuth token found, falling back to legacy Slack bot")
        except Exception as e:
            logger.warning(f"Error trying OAuth method: {e}, falling back to legacy Slack bot")

        if not agent_id:
            logger.error("No agent_id in runtime_context")
            return None

        async for db in get_async_db():
            # Find active Slack bot for this agent
            result = await db.execute(
                select(SlackBot).filter(SlackBot.agent_id == agent_id, SlackBot.connection_status == "connected")
            )
            slack_bot = result.scalar_one_or_none()

            if not slack_bot:
                logger.warning(f"No active Slack bot found for agent {agent_id}")
                return None

            # Decrypt bot token
            bot_token = decrypt_value(slack_bot.slack_bot_token)
            logger.info(f"✅ Using legacy Slack bot for agent {agent_id}")
            return AsyncWebClient(token=bot_token)

    except Exception as e:
        logger.error(f"Error getting Slack client: {e}", exc_info=True)
        return None


async def internal_slack_list_channels(
    include_private: bool = False, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    List all Slack channels the bot can see.

    Args:
        include_private: Whether to include private channels
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with channels list and metadata
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available. Please connect a Slack bot first."}

        channels = []
        cursor = None

        while True:
            response = await client.conversations_list(
                exclude_archived=True,
                types="public_channel,private_channel" if include_private else "public_channel",
                cursor=cursor,
                limit=200,
            )

            for channel in response.get("channels", []):
                channels.append(
                    {
                        "id": channel.get("id"),
                        "name": channel.get("name"),
                        "is_private": channel.get("is_private", False),
                        "is_member": channel.get("is_member", False),
                        "num_members": channel.get("num_members", 0),
                        "topic": channel.get("topic", {}).get("value", ""),
                        "purpose": channel.get("purpose", {}).get("value", ""),
                    }
                )

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return {"success": True, "channels": channels, "total": len(channels)}

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error listing channels: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_read_channel_messages(
    channel_id: str,
    limit: int = 50,
    hours_ago: int | None = None,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Read recent messages from a Slack channel.

    The agent can use this to understand what's being discussed in a channel
    and decide if/how to participate.

    Args:
        channel_id: Slack channel ID (e.g., "C1234567890")
        limit: Maximum number of messages to retrieve (default 50, max 1000)
        hours_ago: Only get messages from the last N hours (optional)
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with messages and context
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        # Calculate oldest timestamp if hours_ago specified
        oldest = None
        if hours_ago:
            oldest_time = datetime.now(UTC) - timedelta(hours=hours_ago)
            oldest = str(oldest_time.timestamp())

        # Get channel messages
        response = await client.conversations_history(channel=channel_id, limit=min(limit, 1000), oldest=oldest)

        # Get channel info
        channel_info = await client.conversations_info(channel=channel_id)
        channel_name = channel_info.get("channel", {}).get("name", "unknown")

        # Process messages
        messages = []
        user_cache = {}

        for msg in response.get("messages", []):
            # Skip bot messages and system messages
            if msg.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue

            user_id = msg.get("user")

            # Get user info (cached)
            if user_id and user_id not in user_cache:
                try:
                    user_info = await client.users_info(user=user_id)
                    user_data = user_info.get("user", {})
                    user_cache[user_id] = {
                        "name": user_data.get("real_name") or user_data.get("name"),
                        "display_name": user_data.get("profile", {}).get("display_name", ""),
                    }
                except:
                    user_cache[user_id] = {"name": "Unknown", "display_name": ""}

            user = user_cache.get(user_id, {"name": "Unknown", "display_name": ""})

            messages.append(
                {
                    "text": msg.get("text", ""),
                    "user_name": user.get("name"),
                    "user_display_name": user.get("display_name"),
                    "timestamp": msg.get("ts"),
                    "thread_ts": msg.get("thread_ts"),
                    "is_thread_reply": bool(msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts")),
                    "reply_count": msg.get("reply_count", 0),
                }
            )

        # Reverse to show oldest first (chronological order)
        messages.reverse()

        return {
            "success": True,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "messages": messages,
            "total_messages": len(messages),
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error reading messages: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_read_thread(
    channel_id: str, thread_ts: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Read all messages in a specific thread.

    Use this when you see a thread with replies and want to understand
    the full conversation context.

    Args:
        channel_id: Slack channel ID
        thread_ts: Thread timestamp (the parent message timestamp)
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with thread messages
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        # Get thread replies
        response = await client.conversations_replies(channel=channel_id, ts=thread_ts)

        # Process messages
        messages = []
        user_cache = {}

        for msg in response.get("messages", []):
            user_id = msg.get("user")

            # Get user info (cached)
            if user_id and user_id not in user_cache:
                try:
                    user_info = await client.users_info(user=user_id)
                    user_data = user_info.get("user", {})
                    user_cache[user_id] = {
                        "name": user_data.get("real_name") or user_data.get("name"),
                        "display_name": user_data.get("profile", {}).get("display_name", ""),
                    }
                except:
                    user_cache[user_id] = {"name": "Unknown", "display_name": ""}

            user = user_cache.get(user_id, {"name": "Unknown", "display_name": ""})

            messages.append(
                {
                    "text": msg.get("text", ""),
                    "user_name": user.get("name"),
                    "timestamp": msg.get("ts"),
                    "is_parent": msg.get("ts") == thread_ts,
                }
            )

        return {
            "success": True,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "messages": messages,
            "total_messages": len(messages),
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error reading thread: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_send_message(
    channel_id: str,
    text: str,
    thread_ts: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Send a message to a Slack channel or thread.

    Use this when you've decided that responding would be valuable.
    Consider the context and only respond when you have something meaningful to contribute.

    Args:
        channel_id: Slack channel ID
        text: Message text to send (supports markdown - will be converted to Slack format)
        thread_ts: Optional thread timestamp to reply in thread
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with send status
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        # Format text for Slack (convert markdown to Slack's mrkdwn format)
        from src.services.slack.formatters import format_text_for_slack

        formatted_text = format_text_for_slack(text)

        response = await client.chat_postMessage(channel=channel_id, text=formatted_text, thread_ts=thread_ts)

        return {
            "success": True,
            "channel_id": channel_id,
            "message_ts": response.get("ts"),
            "thread_ts": thread_ts,
            "message": "Message sent successfully",
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_join_channel(
    channel_id: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Join a Slack channel.

    Use this when you need to participate in a channel you're not currently a member of.

    Args:
        channel_id: Slack channel ID to join
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with join status
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        response = await client.conversations_join(channel=channel_id)

        channel_name = response.get("channel", {}).get("name", "unknown")

        return {
            "success": True,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "message": f"Successfully joined #{channel_name}",
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error joining channel: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_search_messages(
    query: str, count: int = 20, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Search for messages across all channels.

    Use this to find discussions about specific topics or keywords.

    Args:
        query: Search query (supports Slack search operators)
        count: Number of results to return (max 100)
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with search results
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        response = await client.search_messages(query=query, count=min(count, 100))

        matches = []
        for match in response.get("messages", {}).get("matches", []):
            matches.append(
                {
                    "text": match.get("text", ""),
                    "username": match.get("username", ""),
                    "channel_name": match.get("channel", {}).get("name", ""),
                    "channel_id": match.get("channel", {}).get("id", ""),
                    "timestamp": match.get("ts", ""),
                    "permalink": match.get("permalink", ""),
                }
            )

        return {
            "success": True,
            "query": query,
            "matches": matches,
            "total_results": response.get("messages", {}).get("total", 0),
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error searching messages: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_add_reaction(
    channel_id: str,
    timestamp: str,
    emoji: str,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Add an emoji reaction to a message.

    Use this for lightweight acknowledgment or to show agreement without sending a message.

    Args:
        channel_id: Slack channel ID
        timestamp: Message timestamp
        emoji: Emoji name (without colons, e.g., "thumbsup" or "eyes")
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with reaction status
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        await client.reactions_add(channel=channel_id, timestamp=timestamp, name=emoji)

        return {
            "success": True,
            "channel_id": channel_id,
            "timestamp": timestamp,
            "emoji": emoji,
            "message": f"Added reaction :{emoji}:",
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error adding reaction: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_slack_send_dm(
    user_id: str, text: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Send a direct message to a Slack user.

    Use this to send private messages directly to users.

    Args:
        user_id: Slack user ID (e.g., "U1234567890")
        text: Message text to send (supports markdown - will be converted to Slack format)
        runtime_context: Runtime context from agent execution
        config: Config dict with _tool_name

    Returns:
        Dictionary with send status
    """
    try:
        client = await _get_slack_client(runtime_context, config)
        if not client:
            return {"success": False, "error": "No Slack connection available"}

        # Format text for Slack (convert markdown to Slack's mrkdwn format)
        from src.services.slack.formatters import format_text_for_slack

        formatted_text = format_text_for_slack(text)

        # Open a DM channel with the user
        dm_response = await client.conversations_open(users=[user_id])
        dm_channel_id = dm_response.get("channel", {}).get("id")

        if not dm_channel_id:
            return {"success": False, "error": "Could not open DM channel"}

        # Send the message
        response = await client.chat_postMessage(channel=dm_channel_id, text=formatted_text)

        return {
            "success": True,
            "user_id": user_id,
            "channel_id": dm_channel_id,
            "message_ts": response.get("ts"),
            "message": "DM sent successfully",
        }

    except SlackApiError as e:
        logger.error(f"Slack API error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error sending DM: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
