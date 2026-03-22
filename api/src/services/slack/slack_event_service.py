"""Slack Event Mode service for handling HTTP webhook events."""

import logging
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.slack_bot import SlackBot
from ...services.agents.agent_manager import AgentManager
from ...services.agents.security import decrypt_value
from ...services.webhooks.signature_verifier import SignatureVerifier
from .slack_message_handler import SlackMessageHandler

logger = logging.getLogger(__name__)


class SlackEventService:
    """Service for handling Slack Event Mode (HTTP webhook) events.

    This service processes incoming webhook requests from Slack's Event API,
    verifies signatures, and delegates message handling to the shared handler.
    """

    def __init__(self, db_session: AsyncSession, agent_manager: AgentManager | None = None):
        """Initialize the event service.

        Args:
            db_session: SQLAlchemy async database session
            agent_manager: Optional shared AgentManager instance
        """
        self.db_session = db_session
        self.agent_manager = agent_manager or AgentManager()
        self.message_handler = SlackMessageHandler(db_session, self.agent_manager)

    def verify_request(
        self,
        slack_bot: SlackBot,
        payload: bytes,
        timestamp: str,
        signature: str,
    ) -> bool:
        """Verify the webhook request signature.

        Args:
            slack_bot: SlackBot instance with signing_secret
            payload: Raw request body bytes
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid
        """
        if not slack_bot.signing_secret:
            logger.error(f"Slack bot {slack_bot.id} has no signing secret configured")
            return False

        try:
            decrypted_secret = decrypt_value(slack_bot.signing_secret)
            return SignatureVerifier.verify_slack(
                timestamp=timestamp,
                signature_header=signature,
                payload=payload,
                secret=decrypted_secret,
            )
        except Exception as e:
            logger.error(f"Error verifying Slack signature: {e}")
            return False

    async def handle_url_verification(self, payload: dict[str, Any]) -> dict[str, str]:
        """Handle Slack URL verification challenge.

        Args:
            payload: Parsed JSON payload with 'challenge' field

        Returns:
            Dict with challenge response
        """
        challenge = payload.get("challenge", "")
        logger.info("Slack URL verification challenge received")
        return {"challenge": challenge}

    async def process_event(self, slack_bot: SlackBot, payload: dict[str, Any]) -> dict[str, str]:
        """Process a Slack event.

        Args:
            slack_bot: SlackBot instance
            payload: Parsed JSON event payload

        Returns:
            Dict with status response
        """
        event = payload.get("event", {})
        event_type = event.get("type", "")

        logger.info(f"Processing Slack event: {event_type} for bot {slack_bot.id}")

        # Handle different event types
        if event_type == "app_mention":
            await self._handle_app_mention(slack_bot, event, payload)
        elif event_type == "message":
            await self._handle_message_event(slack_bot, event, payload)
        else:
            logger.info(f"Unhandled event type: {event_type}")

        return {"status": "ok"}

    async def _handle_app_mention(self, slack_bot: SlackBot, event: dict[str, Any], payload: dict[str, Any]) -> None:
        """Handle @mention of the bot in a channel.

        Args:
            slack_bot: SlackBot instance
            event: Event data
            payload: Full event payload
        """
        channel_id = event.get("channel", "")
        user_id = event.get("user", "")
        text = event.get("text", "")
        message_ts = event.get("ts")
        thread_ts = event.get("thread_ts")

        if not channel_id or not user_id:
            logger.warning("Missing channel_id or user_id in app_mention event")
            return

        # Create Slack client
        client = await self._get_slack_client(slack_bot)

        # Delegate to shared message handler
        await self.message_handler.handle_message(
            slack_bot=slack_bot,
            channel_id=channel_id,
            user_id=user_id,
            text=text,
            message_ts=message_ts,
            thread_ts=thread_ts,
            client=client,
            say=None,  # Event mode uses client.chat_postMessage
        )

    async def _handle_message_event(self, slack_bot: SlackBot, event: dict[str, Any], payload: dict[str, Any]) -> None:
        """Handle direct messages and channel messages.

        Args:
            slack_bot: SlackBot instance
            event: Event data
            payload: Full event payload
        """
        # Ignore bot messages and message subtypes
        subtype = event.get("subtype")
        if subtype == "bot_message" or event.get("bot_id"):
            return

        if subtype in ("message_changed", "message_deleted", "channel_join", "channel_leave"):
            return

        channel_id = event.get("channel", "")
        channel_type = event.get("channel_type")
        user_id = event.get("user", "")
        text = event.get("text", "")
        message_ts = event.get("ts")
        thread_ts = event.get("thread_ts")

        # Check if this is a DM
        is_dm = channel_type == "im" or channel_id.startswith("D")

        if not is_dm:
            # For channel messages, only respond to @mentions (handled by app_mention event)
            return

        if not channel_id or not user_id:
            logger.warning("Missing channel_id or user_id in message event")
            return

        logger.info(f"Received DM in channel {channel_id} from user {user_id}")

        # Create Slack client
        client = await self._get_slack_client(slack_bot)

        # Delegate to shared message handler
        await self.message_handler.handle_message(
            slack_bot=slack_bot,
            channel_id=channel_id,
            user_id=user_id,
            text=text,
            message_ts=message_ts,
            thread_ts=thread_ts,
            client=client,
            say=None,  # Event mode uses client.chat_postMessage
        )

    async def _get_slack_client(self, slack_bot: SlackBot) -> AsyncWebClient:
        """Create Slack web client for the bot.

        Args:
            slack_bot: SlackBot instance

        Returns:
            Configured AsyncWebClient
        """
        bot_token = decrypt_value(slack_bot.slack_bot_token)
        return AsyncWebClient(token=bot_token)
