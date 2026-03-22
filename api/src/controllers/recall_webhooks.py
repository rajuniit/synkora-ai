"""
Recall.ai Webhook Handler

Receives webhook events from Recall.ai for meeting bot status changes,
transcripts, and participant events.
"""

import json
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.models.oauth_app import OAuthApp
from src.services.agents.security import decrypt_value
from src.services.recall.recall_service import RecallService

logger = logging.getLogger(__name__)

public_router = APIRouter()


# Status messages for user-friendly notifications
STATUS_MESSAGES = {
    "ready": "Meeting bot is ready and waiting to join.",
    "joining_call": "Meeting bot is joining the call...",
    "in_waiting_room": "Meeting bot is in the waiting room. Please admit the bot to start recording.",
    "in_call_not_recording": "Meeting bot has joined but is not recording yet.",
    "in_call_recording": "Meeting bot is now recording the meeting.",
    "call_ended": "The meeting has ended.",
    "done": "Meeting recording is complete! Transcript and recording are now available.",
    "fatal": "Meeting bot encountered an error and could not complete the recording.",
    "analysis_done": "Meeting analysis and processing is complete.",
}


def _get_status_message(status_code: str, bot_id: str) -> str:
    """Get a user-friendly status message."""
    base_message = STATUS_MESSAGES.get(status_code, f"Bot status: {status_code}")
    return f"[Bot {bot_id[:8]}...] {base_message}"


async def _store_meeting_notification(
    db: AsyncSession,
    agent_id: str,
    bot_id: str,
    event_type: str,
    status: str,
    message: str,
):
    """Store a meeting notification for the agent to retrieve."""
    try:
        from src.models.agent_notification import AgentNotification

        notification = AgentNotification(
            agent_id=agent_id,
            notification_type="recall_meeting",
            title=f"Meeting Update: {status}",
            message=message,
            metadata={
                "bot_id": bot_id,
                "event_type": event_type,
                "status": status,
            },
        )
        db.add(notification)
        await db.commit()
        logger.info(f"Stored meeting notification for agent {agent_id}: {event_type}")
    except ImportError:
        # AgentNotification model doesn't exist yet, just log
        logger.info(f"Meeting notification (no storage): agent={agent_id}, event={event_type}, status={status}")
    except Exception as e:
        logger.warning(f"Failed to store meeting notification: {e}")


class RecallWebhookRateLimiter:
    """Rate limiter for Recall.ai webhook endpoints."""

    def __init__(self, requests_per_minute: int = 120, requests_per_hour: int = 5000):
        # Higher limits for Recall - can have many transcript events per meeting
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_window: dict[str, list[float]] = defaultdict(list)
        self.hour_window: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def is_rate_limited(self, key: str) -> tuple[bool, str]:
        """Check if rate limited."""
        current_time = time.time()
        self._cleanup_if_needed(current_time)

        minute_requests = [t for t in self.minute_window[key] if current_time - t < 60]
        if len(minute_requests) >= self.requests_per_minute:
            return True, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"

        hour_requests = [t for t in self.hour_window[key] if current_time - t < 3600]
        if len(hour_requests) >= self.requests_per_hour:
            return True, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"

        return False, ""

    def record_request(self, key: str) -> None:
        """Record a request."""
        current_time = time.time()
        self.minute_window[key].append(current_time)
        self.hour_window[key].append(current_time)

    def _cleanup_if_needed(self, current_time: float) -> None:
        """Clean up old entries."""
        if current_time - self._last_cleanup < 300:
            return

        self._last_cleanup = current_time

        for key in list(self.minute_window.keys()):
            self.minute_window[key] = [t for t in self.minute_window[key] if current_time - t < 60]
            if not self.minute_window[key]:
                del self.minute_window[key]

        for key in list(self.hour_window.keys()):
            self.hour_window[key] = [t for t in self.hour_window[key] if current_time - t < 3600]
            if not self.hour_window[key]:
                del self.hour_window[key]


recall_rate_limiter = RecallWebhookRateLimiter()


async def _get_webhook_secret(db: AsyncSession) -> str | None:
    """Get Recall.ai webhook secret from OAuthApp config."""
    try:
        # Find any active Recall.ai OAuth app (webhook secret is shared across tenant)
        result = await db.execute(
            select(OAuthApp).filter(
                OAuthApp.provider.ilike("recall"),
                OAuthApp.is_active.is_(True),
            )
        )
        oauth_app = result.scalar_one_or_none()

        if not oauth_app:
            return None

        # Get webhook_secret from config JSON
        if oauth_app.config and isinstance(oauth_app.config, dict):
            secret = oauth_app.config.get("webhook_secret")
            if secret and secret.startswith("enc:"):
                secret = decrypt_value(secret)
            return secret

        return None

    except Exception as e:
        logger.error(f"Failed to get Recall webhook secret: {e}")
        return None


@public_router.post("/api/webhooks/recall")
async def receive_recall_webhook(request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Receive webhook events from Recall.ai.

    Events handled:
    - bot.status_change: Bot status updates (joining, recording, done)
    - transcript.data: Real-time transcript segments
    - transcript.partial_data: Partial/interim transcript updates
    - participant_events.join: Participant joined meeting
    - participant_events.leave: Participant left meeting
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Rate limit check
    is_limited, limit_reason = recall_rate_limiter.is_rate_limited(client_ip)
    if is_limited:
        logger.warning(f"Rate limit exceeded for Recall webhook from {client_ip}")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=limit_reason)

    recall_rate_limiter.record_request(client_ip)

    # Get request body
    try:
        payload = await request.body()
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty request body")

        event_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Verify webhook signature if secret is configured
    webhook_secret = await _get_webhook_secret(db)
    if webhook_secret:
        signature = request.headers.get("X-Recall-Signature")
        if not signature:
            logger.warning("Missing X-Recall-Signature header")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")

        if not RecallService.verify_webhook_signature(payload, signature, webhook_secret):
            logger.warning("Invalid Recall webhook signature")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Extract event type
    event_type = event_data.get("event")
    bot_id = event_data.get("data", {}).get("bot", {}).get("id")

    # Get agent_id from query params if provided
    agent_id = request.query_params.get("agent_id")

    logger.info(f"Received Recall webhook: event={event_type}, bot_id={bot_id}, agent_id={agent_id}")

    # Process event based on type
    try:
        if event_type == "bot.status_change":
            await _handle_bot_status_change(db, event_data, agent_id)
        elif event_type == "transcript.data":
            await _handle_transcript_data(db, event_data, agent_id)
        elif event_type == "transcript.partial_data":
            # Partial transcripts - can be used for real-time display
            logger.debug(f"Received partial transcript for bot {bot_id}")
        elif event_type in ["participant_events.join", "participant_events.leave"]:
            await _handle_participant_event(db, event_data, agent_id)
        else:
            logger.info(f"Unhandled Recall event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing Recall webhook: {e}", exc_info=True)
        # Don't fail the webhook - Recall will retry on 5xx errors

    # Always return 200 to acknowledge receipt
    return {"status": "ok", "event": event_type}


async def _handle_bot_status_change(db: AsyncSession, event_data: dict, agent_id: str | None):
    """Handle bot status change events."""
    data = event_data.get("data", {})
    bot_info = data.get("bot", {})
    status_info = data.get("status", {})

    bot_id = bot_info.get("id")
    status_code = status_info.get("code")
    status_message = status_info.get("message")

    logger.info(f"Bot {bot_id} status changed to: {status_code} - {status_message}")

    # Store notification for agent
    if agent_id:
        await _store_meeting_notification(
            db=db,
            agent_id=agent_id,
            bot_id=bot_id,
            event_type="status_change",
            status=status_code,
            message=_get_status_message(status_code, bot_id),
        )

    # When meeting is complete, trigger transcript retrieval notification
    if status_code == "done" and agent_id:
        logger.info(f"Meeting complete for bot {bot_id}. Notifying agent {agent_id}.")
        await _store_meeting_notification(
            db=db,
            agent_id=agent_id,
            bot_id=bot_id,
            event_type="meeting_complete",
            status="done",
            message=f"Meeting recording complete! Bot {bot_id} has finished recording. You can now retrieve the transcript and recording using the bot ID.",
        )


async def _handle_transcript_data(db: AsyncSession, event_data: dict, agent_id: str | None):
    """Handle real-time transcript data events."""
    data = event_data.get("data", {})
    transcript_data = data.get("data", {})
    participant = transcript_data.get("participant", {})
    words = transcript_data.get("words", [])

    if words:
        text = " ".join([w.get("text", "") for w in words])
        speaker = participant.get("name", "Unknown")
        logger.debug(f"Transcript segment: [{speaker}] {text[:100]}...")

    # For post-meeting processing, we don't need to store real-time segments
    # The full transcript will be fetched after the meeting is complete
    # This handler is here for future real-time voice agent implementation


async def _handle_participant_event(db: AsyncSession, event_data: dict, agent_id: str | None):
    """Handle participant join/leave events."""
    data = event_data.get("data", {})
    bot_info = data.get("bot", {})
    participant = data.get("participant", {})
    event_type = event_data.get("event", "")

    bot_id = bot_info.get("id", "unknown")
    participant_name = participant.get("name", "Unknown")
    action = "joined" if "join" in event_type else "left"

    logger.info(f"Participant {participant_name} {action} the meeting")

    # Store notification for agent
    if agent_id:
        await _store_meeting_notification(
            db=db,
            agent_id=agent_id,
            bot_id=bot_id,
            event_type=f"participant_{action}",
            status=action,
            message=f"Participant '{participant_name}' {action} the meeting.",
        )
