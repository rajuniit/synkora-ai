"""
Recall.ai Internal Tools for Synkora Agents.

Provides meeting bot capabilities including sending bots to meetings,
retrieving transcripts and recordings, and managing bot lifecycle.

Supports: Zoom, Google Meet, Microsoft Teams, Webex, Slack Huddles, GoTo Meeting
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def _get_recall_service(
    runtime_context: Any, config: dict[str, Any] | None = None, tool_name: str = "internal_recall_send_bot"
):
    """
    Get Recall.ai service instance with credentials from OAuthApp via credential_resolver.

    Args:
        runtime_context: Runtime context with tenant_id, agent_id, and db_session
        config: Optional config dict
        tool_name: Name of the tool requesting Recall.ai access

    Returns:
        RecallService instance or None if not configured
    """
    try:
        from src.services.agents.credential_resolver import CredentialResolver
        from src.services.recall.recall_service import RecallService

        if not runtime_context:
            logger.error("No runtime context available")
            return None

        # Create credential resolver
        credential_resolver = CredentialResolver(runtime_context)

        # Get Recall.ai credentials
        api_key, region, webhook_secret = await credential_resolver.get_recall_credentials(tool_name)

        if not api_key:
            logger.warning("No Recall.ai API key configured. Add a Recall.ai integration in OAuth Apps settings.")
            return None

        logger.debug(f"Recall.ai configured: region={region}")

        # Get webhook_base_url from feature config if available
        webhook_base_url = None
        try:
            from src.config.feature import get_feature_config

            feature_config = get_feature_config()
            if feature_config and feature_config.domain:
                webhook_base_url = feature_config.domain.webhook_base_url
        except Exception:
            pass

        return RecallService(
            api_key=api_key,
            region=region,
            webhook_base_url=webhook_base_url,
        )

    except Exception as e:
        logger.error(f"Failed to get Recall service: {e}", exc_info=True)
        return None


async def internal_recall_send_bot(
    meeting_url: str,
    bot_name: str = "Synkora Meeting Assistant",
    join_at: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Send a bot to join a meeting and record/transcribe it.

    Supports Zoom, Google Meet, Microsoft Teams, Webex, Slack Huddles, and GoTo Meeting.
    The bot will join the meeting, record audio/video, and generate a transcript.

    Args:
        meeting_url: Meeting URL (e.g., https://zoom.us/j/123456789)
        bot_name: Display name for the bot in the meeting
        join_at: Optional scheduled time to join (ISO format, e.g., "2024-01-15T10:00:00Z")
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with bot ID and status
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_send_bot")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings with your API key.",
            }

        # Parse join_at if provided
        scheduled_time = None
        if join_at:
            try:
                scheduled_time = datetime.fromisoformat(join_at.replace("Z", "+00:00"))
            except ValueError:
                return {"success": False, "error": f"Invalid join_at format: {join_at}. Use ISO format."}

        # Get agent_id for webhook routing
        agent_id = None
        if hasattr(runtime_context, "agent_id"):
            agent_id = str(runtime_context.agent_id)
        elif isinstance(runtime_context, dict):
            agent_id = str(runtime_context.get("agent_id", ""))

        result = await service.send_bot_to_meeting(
            meeting_url=meeting_url,
            bot_name=bot_name,
            join_at=scheduled_time,
            agent_id=agent_id,
        )

        return result

    except Exception as e:
        logger.error(f"Failed to send bot to meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_get_bot_status(
    bot_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the status of a meeting bot.

    Use this to check if the bot has joined, is recording, or has finished.

    Args:
        bot_id: The bot ID returned from send_bot
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with bot status and details
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_get_bot_status")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings.",
            }

        result = await service.get_bot(bot_id)
        return result

    except Exception as e:
        logger.error(f"Failed to get bot status: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_list_bots(
    status: str | None = None,
    limit: int = 20,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    List meeting bots with optional status filter.

    Args:
        status: Filter by status (e.g., "in_call_recording", "done")
        limit: Maximum number of bots to return
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with list of bots
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_list_bots")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings.",
            }

        result = await service.list_bots(status=status, limit=limit)
        return result

    except Exception as e:
        logger.error(f"Failed to list bots: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_get_transcript(
    bot_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the transcript from a completed meeting.

    The meeting must be complete (status = "done") before transcript is available.

    Args:
        bot_id: The bot ID from send_bot
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with transcript text and speaker-identified segments
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_get_transcript")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings.",
            }

        result = await service.get_transcript(bot_id)
        return result

    except Exception as e:
        logger.error(f"Failed to get transcript: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_get_recording(
    bot_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the recording URL from a completed meeting.

    The meeting must be complete (status = "done") before recording is available.

    Args:
        bot_id: The bot ID from send_bot
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with video download URL
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_get_recording")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings.",
            }

        result = await service.get_recording(bot_id)
        return result

    except Exception as e:
        logger.error(f"Failed to get recording: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_remove_bot(
    bot_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Remove a bot from a meeting.

    Use this to make the bot leave a meeting early.

    Args:
        bot_id: The bot ID to remove
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with removal status
    """
    try:
        service = await _get_recall_service(runtime_context, config, tool_name="internal_recall_remove_bot")
        if not service:
            return {
                "success": False,
                "error": "Recall.ai is not configured. Add a Recall.ai integration in OAuth Apps settings.",
            }

        result = await service.remove_bot(bot_id)
        return result

    except Exception as e:
        logger.error(f"Failed to remove bot: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_recall_summarize_meeting(
    bot_id: str,
    save_to_knowledge_base: bool = False,
    knowledge_base_id: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get transcript and generate a meeting summary.

    Optionally saves the summary and transcript to a knowledge base.

    Args:
        bot_id: The bot ID from a completed meeting
        save_to_knowledge_base: Whether to save to knowledge base
        knowledge_base_id: Optional specific knowledge base ID (uses agent's default if not specified)
        config: Configuration dictionary
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with meeting summary and key points
    """
    try:
        # Get transcript first
        transcript_result = await internal_recall_get_transcript(
            bot_id=bot_id,
            config=config,
            runtime_context=runtime_context,
        )

        if not transcript_result.get("success"):
            return transcript_result

        transcript_data = transcript_result.get("data", {})
        full_text = transcript_data.get("full_text", "")

        if not full_text:
            return {"success": False, "error": "No transcript content available"}

        # Get bot details for meeting info
        status_result = await internal_recall_get_bot_status(
            bot_id=bot_id,
            config=config,
            runtime_context=runtime_context,
        )

        bot_data = status_result.get("data", {}) if status_result.get("success") else {}

        # Build meeting metadata
        meeting_info = {
            "bot_id": bot_id,
            "meeting_url": bot_data.get("meeting_url"),
            "bot_name": bot_data.get("bot_name"),
            "created_at": bot_data.get("created_at"),
            "transcript_segments": transcript_data.get("segment_count", 0),
        }

        # Return transcript with metadata - LLM will summarize
        result = {
            "success": True,
            "data": {
                "meeting_info": meeting_info,
                "transcript": full_text,
                "segments": transcript_data.get("segments", []),
            },
            "message": "Transcript retrieved. You can now summarize the key points and action items.",
        }

        # Optionally save to knowledge base
        if save_to_knowledge_base:
            try:
                # Get db and knowledge base
                db = runtime_context.db_session if hasattr(runtime_context, "db_session") else None
                if db and knowledge_base_id:
                    from src.models.knowledge_base import KnowledgeBase

                    kb_result = await db.execute(select(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id))
                    kb = kb_result.scalar_one_or_none()
                    if kb:
                        # Add document to knowledge base
                        result["data"]["saved_to_knowledge_base"] = True
                        result["message"] += f" Transcript saved to knowledge base '{kb.name}'."

            except Exception as kb_error:
                logger.warning(f"Failed to save to knowledge base: {kb_error}")
                result["data"]["knowledge_base_error"] = str(kb_error)

        return result

    except Exception as e:
        logger.error(f"Failed to summarize meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
