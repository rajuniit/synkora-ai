"""Slack Socket Mode service for handling real-time events."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.conversation import Conversation, ConversationStatus
from ...models.message import Message
from ...models.slack_bot import SlackBot, SlackConversation
from ...services.agents.agent_manager import AgentManager
from ...services.agents.security import decrypt_value
from .slack_status_service import SlackStatusService

logger = logging.getLogger(__name__)


class SlackSocketService:
    """Service for managing Slack Socket Mode connections and events."""

    # Class-level storage for active handlers (shared across all instances)
    _active_handlers: dict[str, AsyncSocketModeHandler] = {}

    def __init__(self, db_session: AsyncSession, agent_manager: AgentManager | None = None):
        self.db_session = db_session
        # OPTIMIZATION: Allow passing a shared AgentManager to avoid re-creation overhead
        self.agent_manager = agent_manager or AgentManager()

    @property
    def active_handlers(self) -> dict[str, AsyncSocketModeHandler]:
        """Access the shared active_handlers dictionary."""
        return SlackSocketService._active_handlers

    async def start_bot(self, slack_bot: SlackBot) -> bool:
        """
        Start a Slack bot with Socket Mode connection.

        Args:
            slack_bot: SlackBot instance to start

        Returns:
            bool: True if started successfully
        """
        try:
            # Decrypt tokens
            bot_token = decrypt_value(slack_bot.slack_bot_token)
            app_token = decrypt_value(slack_bot.slack_app_token)

            # Create Slack app
            app = AsyncApp(token=bot_token)

            # Auto-detect workspace info if not set
            if not slack_bot.slack_workspace_id:
                try:
                    client = AsyncWebClient(token=bot_token)
                    auth_response = await client.auth_test()
                    slack_bot.slack_workspace_id = auth_response["team_id"]
                    slack_bot.slack_workspace_name = auth_response["team"]
                    logger.info(
                        f"Auto-detected workspace: {slack_bot.slack_workspace_name} ({slack_bot.slack_workspace_id})"
                    )
                except Exception as e:
                    logger.warning(f"Failed to auto-detect workspace info: {str(e)}")

            # Register event handlers
            self._register_event_handlers(app, slack_bot)

            # Create Socket Mode handler
            handler = AsyncSocketModeHandler(app, app_token)

            # Start the handler in background
            asyncio.create_task(handler.start_async())

            # Store handler reference
            self.active_handlers[str(slack_bot.id)] = handler

            # Update bot status
            slack_bot.connection_status = "connected"
            slack_bot.last_connected_at = datetime.now(UTC)
            await self.db_session.commit()

            logger.info(f"Started Slack bot {slack_bot.bot_name} (ID: {slack_bot.id})")
            return True

        except Exception as e:
            logger.error(f"Failed to start Slack bot {slack_bot.id}: {str(e)}")
            slack_bot.connection_status = "error"
            await self.db_session.commit()
            return False

    async def stop_bot(self, slack_bot_id: UUID) -> bool:
        """
        Stop a running Slack bot.

        Args:
            slack_bot_id: ID of the bot to stop

        Returns:
            bool: True if stopped successfully
        """
        try:
            bot_id_str = str(slack_bot_id)

            if bot_id_str in self.active_handlers:
                handler = self.active_handlers[bot_id_str]
                await handler.close_async()
                del self.active_handlers[bot_id_str]

                logger.info(f"Stopped Slack bot {slack_bot_id}")
            else:
                logger.info(f"Slack bot {slack_bot_id} was not running in active handlers")

            # Update bot status regardless of whether it was in active_handlers
            slack_bot = await self.db_session.get(SlackBot, slack_bot_id)
            if slack_bot:
                slack_bot.connection_status = "disconnected"
                await self.db_session.commit()

            # Always return True - stopping an already-stopped bot is not an error
            return True

        except Exception as e:
            logger.error(f"Failed to stop Slack bot {slack_bot_id}: {str(e)}")
            return False

    def _register_event_handlers(self, app: AsyncApp, slack_bot: SlackBot):
        """Register event handlers for the Slack app."""

        @app.event("app_mention")
        async def handle_app_mention(event, say, client):
            """Handle @mentions of the bot."""
            await self._handle_message(
                slack_bot=slack_bot,
                channel_id=event["channel"],
                user_id=event["user"],
                text=event["text"],
                message_ts=event.get("ts"),
                thread_ts=event.get("thread_ts"),
                say=say,
                client=client,
            )

        @app.event("message")
        async def handle_message(event, say, client):
            """Handle all messages for autonomous monitoring."""
            # Ignore bot messages and message subtypes (edits, deletions, etc.)
            subtype = event.get("subtype")
            if subtype == "bot_message" or event.get("bot_id"):
                return

            # Ignore message subtypes like edits, deletions, etc.
            if subtype in ("message_changed", "message_deleted", "channel_join", "channel_leave"):
                return

            channel_id = event.get("channel", "")
            channel_type = event.get("channel_type")

            # Detect DMs: channel_type is "im" OR channel ID starts with "D"
            # (DM channel IDs in Slack start with 'D')
            is_dm = channel_type == "im" or channel_id.startswith("D")

            if is_dm:
                logger.info(f"Received DM in channel {channel_id} from user {event.get('user')}")
                await self._handle_message(
                    slack_bot=slack_bot,
                    channel_id=channel_id,
                    user_id=event["user"],
                    text=event.get("text", ""),
                    message_ts=event.get("ts"),
                    thread_ts=event.get("thread_ts"),  # Support threaded DMs
                    say=say,
                    client=client,
                )
                return

            # For channel messages, only respond to @mentions (handled by app_mention event)
            # This prevents the bot from responding to every message in the channel

    async def _handle_message(
        self,
        slack_bot: SlackBot,
        channel_id: str,
        user_id: str,
        text: str,
        message_ts: str | None,
        thread_ts: str | None,
        say,
        client: AsyncWebClient,
    ):
        """
        Handle incoming Slack message and generate agent response.

        Args:
            slack_bot: SlackBot instance
            channel_id: Slack channel ID
            user_id: Slack user ID
            text: Message text
            message_ts: Message timestamp
            thread_ts: Thread timestamp (for threaded conversations)
            say: Slack say function
            client: Slack web client
        """
        try:
            # Get or create conversation mapping
            conversation = await self._get_or_create_conversation(
                slack_bot=slack_bot, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts
            )

            # OPTIMIZATION: Fetch user, channel, and auth info in parallel (~600ms saved)
            user_info, channel_info, auth_info = await asyncio.gather(
                client.users_info(user=user_id),
                client.conversations_info(channel=channel_id),
                client.auth_test(),
            )
            user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
            channel_name = channel_info.get("channel", {}).get("name", "unknown")
            team_domain = auth_info.get("url", "").replace("https://", "").replace(".slack.com/", "")

            # Generate Slack permalink
            # Format: https://{team}.slack.com/archives/{channel_id}/p{timestamp_without_dot}
            permalink = None
            if message_ts and team_domain:
                # Remove the dot from timestamp (e.g., 1234567890.123456 -> 1234567890123456)
                ts_for_url = message_ts.replace(".", "")
                permalink = f"https://{team_domain}.slack.com/archives/{channel_id}/p{ts_for_url}"

            # Remove bot mention from text if present
            clean_text = self._remove_bot_mention(text, slack_bot.slack_app_id)

            # Extract mentions from the message, filtering out bot users
            mentioned_users = await self._extract_user_mentions(clean_text, client)

            # Enhanced message to provide context to the agent
            # This helps the agent understand WHERE the message came from
            mentions_info = ""
            if mentioned_users:
                user_list = ", ".join([f"{u['name']} ({u['id']})" for u in mentioned_users])
                mentions_info = f", Mentioned Users: {user_list}"

            permalink_info = f", Message Link: {permalink}" if permalink else ""

            context_message = f"""[Slack Context: Channel #{channel_name} (ID: {channel_id}), Message Timestamp: {message_ts}{mentions_info}{permalink_info}]

{clean_text}"""

            # LOG: Verify context message creation
            logger.info("CONTEXT MESSAGE CREATED:")
            logger.info(f"   Channel: #{channel_name} (ID: {channel_id})")
            logger.info(f"   Message TS: {message_ts}")
            logger.info(f"   Clean Text: {clean_text[:100]}...")
            logger.info(f"   Full Context Message: {context_message[:200]}...")

            # Save user message with enhanced metadata
            from ...models.message import MessageRole

            user_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=context_message,
                message_metadata={
                    "slack_user_id": user_id,
                    "slack_user_name": user_name,
                    "slack_channel_id": channel_id,
                    "slack_channel_name": channel_name,
                    "slack_message_ts": message_ts,
                    "slack_thread_ts": thread_ts,
                    "original_text": text,
                },
            )
            self.db_session.add(user_message)
            conversation.increment_message_count()
            # OPTIMIZATION: Use flush() instead of commit() - saves ~100-200ms by avoiding fsync
            # The final commit happens after assistant message is saved
            await self.db_session.flush()

            # Use native Slack status indicator instead of posting a message
            # This shows "BotName is thinking..." without cluttering the conversation
            status_service = SlackStatusService(client)
            effective_thread_ts = thread_ts or message_ts
            await status_service.set_thinking(channel_id, effective_thread_ts)

            # Get agent response using the existing chat infrastructure
            from ...models.agent import Agent
            from ...services.agents.agent_loader_service import AgentLoaderService
            from ...services.agents.chat_service import ChatService
            from ...services.agents.chat_stream_service import ChatStreamService
            from ...services.conversation_service import ConversationService

            # Get agent name from database (avoid lazy loading issues)
            agent = await self.db_session.get(Agent, slack_bot.agent_id)
            if not agent:
                raise ValueError(f"Agent {slack_bot.agent_id} not found")

            # Load conversation history with caching support
            conversation_history = await ConversationService.get_conversation_history_cached(
                db=self.db_session,
                conversation_id=conversation.id,
                limit=30,  # Keep recent messages for context
            )
            logger.info(f"Loaded {len(conversation_history)} messages from conversation history")

            # IMPORTANT: Fetch Slack thread history to provide full context
            # This ensures the LLM has access to the entire thread conversation
            thread_context = []
            # OPTIMIZATION: Only fetch thread if this is a reply to an existing thread
            # Skip for first messages (thread_ts is None) or messages that start a thread (thread_ts == message_ts)
            # This saves ~300ms API call for non-threaded messages
            effective_thread_ts = thread_ts if thread_ts and thread_ts != message_ts else None
            if effective_thread_ts:
                try:
                    thread_replies = await client.conversations_replies(
                        channel=channel_id,
                        ts=effective_thread_ts,
                        limit=50,  # Get up to 50 messages from thread
                        inclusive=True,  # Include the parent message
                    )

                    if thread_replies.get("ok") and thread_replies.get("messages"):
                        thread_messages = thread_replies["messages"]
                        logger.info(f"Fetched {len(thread_messages)} messages from Slack thread {effective_thread_ts}")

                        # OPTIMIZATION: Batch fetch all unique user IDs in parallel (~1-4s saved)
                        # First pass: collect unique user IDs from non-bot messages
                        user_ids_to_fetch = set()
                        for msg in thread_messages:
                            if msg.get("ts") == message_ts:
                                continue
                            if not msg.get("bot_id") and msg.get("user") and msg.get("text", "").strip():
                                user_ids_to_fetch.add(msg.get("user"))

                        # Fetch all users in parallel
                        user_map: dict[str, str] = {}
                        if user_ids_to_fetch:
                            user_tasks = [client.users_info(user=uid) for uid in user_ids_to_fetch]
                            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
                            for result in user_results:
                                if isinstance(result, Exception):
                                    continue
                                user_data = result.get("user", {})
                                uid = user_data.get("id")
                                if uid:
                                    user_map[uid] = user_data.get("real_name") or user_data.get("name", "User")

                        # Second pass: build thread context using the user map
                        for msg in thread_messages:
                            msg_ts = msg.get("ts")
                            # Skip the current message we're processing (it will be added by the LLM flow)
                            if msg_ts == message_ts:
                                continue

                            msg_text = msg.get("text", "")
                            msg_user = msg.get("user")
                            bot_id = msg.get("bot_id")

                            # Skip empty messages or system messages
                            if not msg_text.strip():
                                continue

                            # Determine role based on whether it's from a bot or user
                            if bot_id:
                                thread_context.append({"role": "assistant", "content": msg_text})
                            else:
                                # Use cached user name from batch fetch
                                sender_name = user_map.get(msg_user, "User") if msg_user else "User"
                                thread_context.append({"role": "user", "content": f"[{sender_name}]: {msg_text}"})

                        logger.info(f"Built thread context with {len(thread_context)} messages")

                except Exception as e:
                    logger.warning(f"Failed to fetch Slack thread history: {e}")

            # Merge Slack thread context with database conversation history
            # Thread context takes precedence as it's the authoritative source for Slack threads
            if thread_context:
                # Use thread context if it has more messages than DB history
                db_history_count = len(conversation_history)
                if len(thread_context) > db_history_count:
                    logger.info(
                        f"Using Slack thread context ({len(thread_context)} messages) instead of DB history ({db_history_count} messages)"
                    )
                    conversation_history = thread_context
                else:
                    logger.info(
                        f"Keeping DB history ({len(conversation_history)} messages) over thread context ({len(thread_context)} messages)"
                    )

            # Initialize the chat stream service
            chat_stream_service = ChatStreamService(
                agent_loader=AgentLoaderService(self.agent_manager), chat_service=ChatService()
            )

            # Collect the streamed response
            response_chunks = []
            async for event_data in chat_stream_service.stream_agent_response(
                agent_name=agent.agent_name,
                message=context_message,  # Use the full context message with header
                conversation_history=conversation_history,  # Pass loaded history for memory
                conversation_id=str(conversation.id),
                attachments=None,
                llm_config_id=None,
                db=self.db_session,
            ):
                # Parse SSE data
                if event_data.startswith("data: "):
                    try:
                        import json

                        event_json = json.loads(event_data[6:])  # Remove "data: " prefix
                        if event_json.get("type") == "chunk":
                            response_chunks.append(event_json.get("content", ""))
                    except:
                        pass

            agent_response = "".join(response_chunks)

            # Handle empty response - this happens when LLM only calls tools without generating text
            if not agent_response or not agent_response.strip():
                logger.warning("Agent returned empty response, using fallback message")
                agent_response = "Done! I've processed your request."

            # Format response for Slack using Block Kit
            from .formatters import chunk_blocks, create_slack_blocks, format_text_for_slack

            # Create blocks from the response
            blocks = create_slack_blocks(agent_response)

            # Double-check blocks aren't empty (shouldn't happen with fallback above)
            if not blocks:
                logger.warning("Block creation resulted in empty blocks, creating simple text block")
                blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": agent_response}}]

            # Check if we need to chunk the response
            if len(blocks) > 50:  # Slack's block limit
                logger.info(f"Response has {len(blocks)} blocks, chunking required")
                block_chunks = chunk_blocks(blocks)

                # Send each chunk as a separate message in thread
                for i, chunk in enumerate(block_chunks):
                    fallback_text = (
                        format_text_for_slack(agent_response) if i == 0 else f"(continued {i + 1}/{len(block_chunks)})"
                    )
                    await say(
                        text=fallback_text,
                        blocks=chunk,
                        thread_ts=thread_ts or message_ts,  # Reply in thread to original message
                    )
            else:
                # Send single message with blocks
                # If no thread exists, start one by using the original message timestamp
                fallback_text = format_text_for_slack(agent_response)
                await say(
                    text=fallback_text,
                    blocks=blocks,
                    thread_ts=thread_ts or message_ts,  # Reply in thread to original message
                )

            # Save agent response
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=agent_response,
            )
            self.db_session.add(assistant_message)
            conversation.increment_message_count()
            # OPTIMIZATION: Single commit for both user and assistant messages (fsync once)
            await self.db_session.commit()

        except Exception as e:
            logger.error(f"Error handling Slack message: {str(e)}")
            # Rollback the session on error
            await self.db_session.rollback()
            await say(
                text="Sorry, I encountered an error processing your message. Please try again.", thread_ts=thread_ts
            )

    async def _get_or_create_conversation(
        self, slack_bot: SlackBot, channel_id: str, user_id: str, thread_ts: str | None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        # Try to find existing conversation
        stmt = select(SlackConversation).where(
            SlackConversation.slack_bot_id == slack_bot.id,
            SlackConversation.slack_channel_id == channel_id,
            SlackConversation.slack_user_id == user_id,
            SlackConversation.slack_thread_ts == thread_ts,
        )
        result = await self.db_session.execute(stmt)
        slack_conv = result.scalar_one_or_none()

        if slack_conv:
            # Return existing conversation
            return await self.db_session.get(Conversation, slack_conv.conversation_id)

        # Create new conversation
        conversation = Conversation(
            agent_id=slack_bot.agent_id, name=f"Slack conversation with {user_id}", status=ConversationStatus.ACTIVE
        )
        self.db_session.add(conversation)
        await self.db_session.commit()
        await self.db_session.refresh(conversation)

        # Create mapping
        slack_conv = SlackConversation(
            slack_bot_id=slack_bot.id,
            conversation_id=conversation.id,
            slack_channel_id=channel_id,
            slack_user_id=user_id,
            slack_thread_ts=thread_ts,
        )
        self.db_session.add(slack_conv)
        await self.db_session.commit()

        return conversation

    def _remove_bot_mention(self, text: str, app_id: str) -> str:
        """Remove bot mention from message text."""
        import re

        # Remove <@BOTID> mentions
        pattern = f"<@{app_id}>"
        return re.sub(pattern, "", text).strip()

    async def _extract_user_mentions(self, text: str, client: AsyncWebClient) -> list:
        """
        Extract user mentions from message text and filter out bots.

        Args:
            text: Message text containing mentions
            client: Slack web client

        Returns:
            List of dicts with user info (id, name, is_bot=False only)
        """
        import re

        # Extract all user IDs from mentions (<@U123456>)
        mention_pattern = r"<@([UW][A-Z0-9]+)>"
        user_ids = re.findall(mention_pattern, text)

        if not user_ids:
            return []

        # OPTIMIZATION: Fetch all mentioned users in parallel
        unique_user_ids = list(set(user_ids))
        user_tasks = [client.users_info(user=uid) for uid in unique_user_ids]
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)

        mentioned_users = []
        for i, result in enumerate(user_results):
            if isinstance(result, Exception):
                logger.warning(f"Could not get info for user {unique_user_ids[i]}: {result}")
                continue

            user_data = result.get("user", {})
            user_id = user_data.get("id")

            # Skip bot users
            if user_data.get("is_bot") or user_data.get("is_app_user"):
                logger.info(f"Skipping bot user: {user_data.get('name')} ({user_id})")
                continue

            # Only include real users
            mentioned_users.append(
                {"id": user_id, "name": user_data.get("real_name") or user_data.get("name", "Unknown")}
            )

        return mentioned_users

    async def get_bot_status(self, slack_bot_id: UUID) -> dict[str, Any]:
        """Get status of a Slack bot."""
        bot_id_str = str(slack_bot_id)
        is_running = bot_id_str in self.active_handlers

        slack_bot = await self.db_session.get(SlackBot, slack_bot_id)

        return {
            "bot_id": str(slack_bot_id),
            "is_running": is_running,
            "connection_status": slack_bot.connection_status if slack_bot else "unknown",
            "last_connected_at": slack_bot.last_connected_at.isoformat()
            if slack_bot and slack_bot.last_connected_at
            else None,
        }
