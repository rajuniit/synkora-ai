"""Shared Slack message handler for Socket Mode and Event Mode."""

import asyncio
import logging
from typing import Any, Callable

from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.conversation import Conversation, ConversationStatus
from ...models.message import Message, MessageRole
from ...models.slack_bot import SlackBot, SlackConversation
from ...services.agents.agent_manager import AgentManager

logger = logging.getLogger(__name__)


class SlackMessageHandler:
    """Shared handler for processing Slack messages.

    This class extracts the common message handling logic that is used by both
    Socket Mode (WebSocket) and Event Mode (HTTP webhooks) connections.
    """

    def __init__(self, db_session: AsyncSession, agent_manager: AgentManager | None = None):
        """Initialize the message handler.

        Args:
            db_session: SQLAlchemy async database session
            agent_manager: Optional shared AgentManager instance
        """
        self.db_session = db_session
        self.agent_manager = agent_manager or AgentManager()

    async def handle_message(
        self,
        slack_bot: SlackBot,
        channel_id: str,
        user_id: str,
        text: str,
        message_ts: str | None,
        thread_ts: str | None,
        client: AsyncWebClient,
        say: Callable[..., Any] | None = None,
    ) -> str | None:
        """
        Handle incoming Slack message and generate agent response.

        Args:
            slack_bot: SlackBot instance
            channel_id: Slack channel ID
            user_id: Slack user ID
            text: Message text
            message_ts: Message timestamp
            thread_ts: Thread timestamp (for threaded conversations)
            client: Slack web client
            say: Optional Slack say function (for Socket Mode). If None, uses client.chat_postMessage

        Returns:
            The agent's response text, or None on error
        """
        try:
            # Get or create conversation mapping
            conversation = await self._get_or_create_conversation(
                slack_bot=slack_bot, channel_id=channel_id, user_id=user_id, thread_ts=thread_ts
            )

            # Fetch user, channel, and auth info in parallel (suppress individual failures)
            user_info: Any
            channel_info: Any
            auth_info: Any
            user_info, channel_info, auth_info = await asyncio.gather(
                client.users_info(user=user_id),
                client.conversations_info(channel=channel_id),
                client.auth_test(),
                return_exceptions=True,
            )
            if isinstance(user_info, Exception):
                logger.warning(f"Could not fetch user info for {user_id}: {user_info}. Missing users:read scope?")
                user_name = user_id
            else:
                user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
            if isinstance(channel_info, Exception):
                logger.warning(
                    f"Could not fetch channel info for {channel_id}: {channel_info}. Missing channels:read scope?"
                )
                channel_name = channel_id
            else:
                channel_name = channel_info.get("channel", {}).get("name", channel_id)
            if isinstance(auth_info, Exception):
                logger.warning(f"Could not fetch auth info: {auth_info}")
                team_domain = ""
            else:
                team_domain = auth_info.get("url", "").replace("https://", "").replace(".slack.com/", "")

            # Generate Slack permalink
            permalink = None
            if message_ts and team_domain:
                ts_for_url = message_ts.replace(".", "")
                permalink = f"https://{team_domain}.slack.com/archives/{channel_id}/p{ts_for_url}"

            # Remove bot mention from text if present
            clean_text = self._remove_bot_mention(text, slack_bot.slack_app_id)

            # Extract mentions from the message, filtering out bot users
            mentioned_users = await self._extract_user_mentions(clean_text, client)

            # Enhanced message to provide context to the agent
            mentions_info = ""
            if mentioned_users:
                user_list = ", ".join([f"{u['name']} ({u['id']})" for u in mentioned_users])
                mentions_info = f", Mentioned Users: {user_list}"

            permalink_info = f", Message Link: {permalink}" if permalink else ""

            context_message = f"""[Slack Context: Channel #{channel_name} (ID: {channel_id}), Message Timestamp: {message_ts}{mentions_info}{permalink_info}]

{clean_text}"""

            logger.info(f"CONTEXT MESSAGE: Channel: #{channel_name} (ID: {channel_id}), Message TS: {message_ts}")

            # Save user message with enhanced metadata
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
            await self.db_session.flush()

            # Use native Slack status indicator
            from .slack_status_service import SlackStatusService

            status_service = SlackStatusService(client)
            effective_thread_ts = thread_ts or message_ts
            await status_service.set_thinking(channel_id, effective_thread_ts)

            # Get agent response using the existing chat infrastructure
            from ...models.agent import Agent
            from ...services.agents.agent_loader_service import AgentLoaderService
            from ...services.agents.chat_service import ChatService
            from ...services.agents.chat_stream_service import ChatStreamService
            from ...services.conversation_service import ConversationService

            # Get agent name from database
            agent = await self.db_session.get(Agent, slack_bot.agent_id)
            if not agent:
                raise ValueError(f"Agent {slack_bot.agent_id} not found")

            # Load conversation history with caching support
            conversation_history = await ConversationService.get_conversation_history_cached(
                db=self.db_session,
                conversation_id=conversation.id,
                limit=30,
            )
            logger.info(f"Loaded {len(conversation_history)} messages from conversation history")

            # Fetch Slack thread history to provide full context
            thread_context = await self._fetch_thread_context(client, channel_id, thread_ts, message_ts)

            # Merge Slack thread context with database conversation history
            if thread_context and len(thread_context) > len(conversation_history):
                logger.info(f"Using Slack thread context ({len(thread_context)} messages) instead of DB history")
                conversation_history = thread_context

            # Initialize the chat stream service
            chat_stream_service = ChatStreamService(
                agent_loader=AgentLoaderService(self.agent_manager), chat_service=ChatService()
            )

            # Collect the streamed response
            response_chunks = []
            async for event_data in chat_stream_service.stream_agent_response(
                agent_name=agent.agent_name,
                message=context_message,
                conversation_history=conversation_history,
                conversation_id=str(conversation.id),
                attachments=None,
                llm_config_id=None,
                db=self.db_session,
            ):
                if event_data.startswith("data: "):
                    try:
                        import json

                        event_json = json.loads(event_data[6:])
                        if event_json.get("type") == "chunk":
                            response_chunks.append(event_json.get("content", ""))
                    except:
                        pass

            agent_response = "".join(response_chunks)

            # Handle empty response
            if not agent_response or not agent_response.strip():
                logger.warning("Agent returned empty response, using fallback message")
                agent_response = "Done! I've processed your request."

            # Send response using appropriate method
            await self._send_response(
                client=client,
                say=say,
                channel_id=channel_id,
                thread_ts=thread_ts or message_ts,
                response=agent_response,
            )

            # Save agent response
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=agent_response,
            )
            self.db_session.add(assistant_message)
            conversation.increment_message_count()
            await self.db_session.commit()

            return agent_response

        except Exception as e:
            logger.error(f"Error handling Slack message: {str(e)}")
            await self.db_session.rollback()
            # Send error message
            error_msg = "Sorry, I encountered an error processing your message. Please try again."
            await self._send_response(
                client=client,
                say=say,
                channel_id=channel_id,
                thread_ts=thread_ts,
                response=error_msg,
            )
            return None

    async def _send_response(
        self,
        client: AsyncWebClient,
        say: Callable[..., Any] | None,
        channel_id: str,
        thread_ts: str | None,
        response: str,
    ) -> None:
        """Send response to Slack using appropriate method.

        Args:
            client: Slack web client
            say: Optional Slack say function (from Socket Mode)
            channel_id: Channel to send to
            thread_ts: Thread timestamp (for threaded replies)
            response: Response text
        """
        from .formatters import chunk_blocks, create_slack_blocks, format_text_for_slack

        # Create blocks from the response
        blocks = create_slack_blocks(response)

        if not blocks:
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": response}}]

        # Check if we need to chunk the response
        if len(blocks) > 50:  # Slack's block limit
            block_chunks = chunk_blocks(blocks)

            for i, chunk in enumerate(block_chunks):
                fallback_text = (
                    format_text_for_slack(response) if i == 0 else f"(continued {i + 1}/{len(block_chunks)})"
                )
                if say:
                    await say(text=fallback_text, blocks=chunk, thread_ts=thread_ts)
                else:
                    await client.chat_postMessage(
                        channel=channel_id,
                        text=fallback_text,
                        blocks=chunk,
                        thread_ts=thread_ts,
                    )
        else:
            fallback_text = format_text_for_slack(response)
            if say:
                await say(text=fallback_text, blocks=blocks, thread_ts=thread_ts)
            else:
                await client.chat_postMessage(
                    channel=channel_id,
                    text=fallback_text,
                    blocks=blocks,
                    thread_ts=thread_ts,
                )

    async def _fetch_thread_context(
        self,
        client: AsyncWebClient,
        channel_id: str,
        thread_ts: str | None,
        message_ts: str | None,
    ) -> list[dict[str, str]]:
        """Fetch thread history from Slack to provide context.

        Args:
            client: Slack web client
            channel_id: Channel ID
            thread_ts: Thread timestamp
            message_ts: Current message timestamp

        Returns:
            List of messages in thread context format
        """
        thread_context = []
        effective_thread_ts = thread_ts if thread_ts and thread_ts != message_ts else None

        if not effective_thread_ts:
            return thread_context

        try:
            thread_replies = await client.conversations_replies(
                channel=channel_id,
                ts=effective_thread_ts,
                limit=50,
                inclusive=True,
            )

            if not thread_replies.get("ok") or not thread_replies.get("messages"):
                return thread_context

            thread_messages = thread_replies["messages"]
            logger.info(f"Fetched {len(thread_messages)} messages from Slack thread {effective_thread_ts}")

            # Batch fetch all unique user IDs
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

            # Build thread context
            for msg in thread_messages:
                msg_ts = msg.get("ts")
                if msg_ts == message_ts:
                    continue

                msg_text = msg.get("text", "")
                msg_user = msg.get("user")
                bot_id = msg.get("bot_id")

                if not msg_text.strip():
                    continue

                if bot_id:
                    thread_context.append({"role": "assistant", "content": msg_text})
                else:
                    sender_name = user_map.get(msg_user, "User") if msg_user else "User"
                    thread_context.append({"role": "user", "content": f"[{sender_name}]: {msg_text}"})

            logger.info(f"Built thread context with {len(thread_context)} messages")

        except Exception as e:
            logger.warning(f"Failed to fetch Slack thread history: {e}")

        return thread_context

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

        pattern = f"<@{app_id}>"
        return re.sub(pattern, "", text).strip()

    async def _extract_user_mentions(self, text: str, client: AsyncWebClient) -> list[dict[str, str]]:
        """Extract user mentions from message text and filter out bots.

        Args:
            text: Message text containing mentions
            client: Slack web client

        Returns:
            List of dicts with user info (id, name, is_bot=False only)
        """
        import re

        mention_pattern = r"<@([UW][A-Z0-9]+)>"
        user_ids = re.findall(mention_pattern, text)

        if not user_ids:
            return []

        # Fetch all mentioned users in parallel
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

            mentioned_users.append(
                {"id": user_id, "name": user_data.get("real_name") or user_data.get("name", "Unknown")}
            )

        return mentioned_users
