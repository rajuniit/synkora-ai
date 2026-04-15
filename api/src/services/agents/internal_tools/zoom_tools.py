"""
Zoom Internal Tools for Synkora Agents.

Provides Zoom meeting management capabilities including creating, listing,
updating, and deleting meetings, as well as accessing meeting recordings.
"""

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Zoom API Base URL
ZOOM_API_BASE = "https://api.zoom.us/v2"


async def _get_zoom_user_timezone(access_token: str) -> str | None:
    """Get the timezone from the authenticated Zoom user's settings."""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ZOOM_API_BASE}/users/me", headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    timezone = user_data.get("timezone")
                    if timezone:
                        logger.info(f"Got Zoom user timezone: {timezone}")
                        return timezone
    except Exception as e:
        logger.warning(f"Failed to get Zoom user timezone: {e}")
    return None


async def internal_zoom_create_meeting(
    topic: str,
    start_time: str,
    duration: int,
    timezone: str = None,
    agenda: str = None,
    password: str = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Create a new Zoom meeting.

    Args:
        topic: Meeting topic/title
        start_time: Start time in ISO 8601 format (e.g., "2025-01-10T10:00:00Z")
        duration: Duration in minutes
        timezone: Timezone (optional, defaults to user's Zoom account timezone)
        agenda: Meeting agenda/description (optional)
        password: Meeting password (optional)
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with:
        - success: bool
        - data: Meeting details (id, join_url, password, etc.)
        - error: str (if failed)
    """
    try:
        # Validate inputs
        if not topic or not isinstance(topic, str):
            return {"success": False, "error": "Meeting topic is required and must be a string"}

        if not start_time or not isinstance(start_time, str):
            return {"success": False, "error": "Start time is required in ISO 8601 format"}

        if not isinstance(duration, int) or duration <= 0:
            return {"success": False, "error": "Duration must be a positive integer (minutes)"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_create_meeting")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Get timezone - if not provided, fetch from user's Zoom account
        meeting_timezone = timezone
        if not meeting_timezone:
            meeting_timezone = await _get_zoom_user_timezone(access_token)
            if not meeting_timezone:
                meeting_timezone = "UTC"  # Final fallback
                logger.warning("Could not determine user timezone, using UTC")

        # Prepare meeting data
        meeting_data = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time,
            "duration": duration,
            "timezone": meeting_timezone,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "watermark": False,
                "use_pmi": False,
                "approval_type": 2,  # No registration required
                "audio": "both",  # Both telephony and VoIP
                "auto_recording": "none",
            },
        }

        if agenda:
            meeting_data["agenda"] = agenda

        if password:
            meeting_data["password"] = password

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session, session.post(
            f"{ZOOM_API_BASE}/users/me/meetings", headers=headers, json=meeting_data
        ) as response:
            if response.status not in [200, 201]:
                error_data = await response.json()
                logger.error(f"Zoom API error: {error_data}")
                return {
                    "success": False,
                    "error": f"Failed to create meeting: {error_data.get('message', 'Unknown error')}",
                }

            result = await response.json()

            logger.info(f"Successfully created Zoom meeting: {result.get('id')}")

            return {
                "success": True,
                "data": {
                    "meeting_id": result.get("id"),
                    "topic": result.get("topic"),
                    "start_time": result.get("start_time"),
                    "duration": result.get("duration"),
                    "timezone": result.get("timezone"),
                    "join_url": result.get("join_url"),
                    "password": result.get("password"),
                    "host_email": result.get("host_email"),
                    "agenda": result.get("agenda"),
                },
                "message": f"Successfully created meeting: {topic}",
            }

    except Exception as e:
        logger.error(f"Failed to create Zoom meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_zoom_list_meetings(
    meeting_type: str = "scheduled",
    page_size: int = 30,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    List user's Zoom meetings.

    Args:
        meeting_type: Type of meetings to list (scheduled, live, upcoming)
        page_size: Number of meetings to return (max 300)
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with:
        - success: bool
        - data: List of meetings
        - error: str (if failed)
    """
    try:
        # Validate meeting type
        valid_types = ["scheduled", "live", "upcoming"]
        if meeting_type not in valid_types:
            return {"success": False, "error": f"Invalid meeting_type. Must be one of: {', '.join(valid_types)}"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_list_meetings")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}"}

        params = {
            "type": meeting_type,
            "page_size": min(page_size, 300),  # Cap at 300
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ZOOM_API_BASE}/users/me/meetings", headers=headers, params=params) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"Zoom API error: {error_data}")
                    return {
                        "success": False,
                        "error": f"Failed to list meetings: {error_data.get('message', 'Unknown error')}",
                    }

                result = await response.json()
                meetings = result.get("meetings", [])

                # Format meeting data
                formatted_meetings = [
                    {
                        "meeting_id": m.get("id"),
                        "topic": m.get("topic"),
                        "start_time": m.get("start_time"),
                        "duration": m.get("duration"),
                        "timezone": m.get("timezone"),
                        "join_url": m.get("join_url"),
                        "agenda": m.get("agenda"),
                    }
                    for m in meetings
                ]

                return {
                    "success": True,
                    "data": {
                        "meetings": formatted_meetings,
                        "total_count": len(formatted_meetings),
                        "meeting_type": meeting_type,
                    },
                    "message": f"Found {len(formatted_meetings)} {meeting_type} meetings",
                }

    except Exception as e:
        logger.error(f"Failed to list Zoom meetings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_zoom_get_meeting(
    meeting_id: str, config: dict[str, Any] | None = None, runtime_context: Any = None
) -> dict[str, Any]:
    """
    Get details of a specific Zoom meeting.

    Args:
        meeting_id: Zoom meeting ID
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with meeting details
    """
    try:
        if not meeting_id:
            return {"success": False, "error": "Meeting ID is required"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_get_meeting")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ZOOM_API_BASE}/meetings/{meeting_id}", headers=headers) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"Zoom API error: {error_data}")
                    return {
                        "success": False,
                        "error": f"Failed to get meeting: {error_data.get('message', 'Unknown error')}",
                    }

                result = await response.json()

                return {
                    "success": True,
                    "data": {
                        "meeting_id": result.get("id"),
                        "topic": result.get("topic"),
                        "start_time": result.get("start_time"),
                        "duration": result.get("duration"),
                        "timezone": result.get("timezone"),
                        "join_url": result.get("join_url"),
                        "password": result.get("password"),
                        "host_email": result.get("host_email"),
                        "agenda": result.get("agenda"),
                        "status": result.get("status"),
                        "created_at": result.get("created_at"),
                    },
                }

    except Exception as e:
        logger.error(f"Failed to get Zoom meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_zoom_update_meeting(
    meeting_id: str,
    topic: str = None,
    start_time: str = None,
    duration: int = None,
    agenda: str = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Update a Zoom meeting.

    Args:
        meeting_id: Zoom meeting ID
        topic: New meeting topic (optional)
        start_time: New start time in ISO 8601 format (optional)
        duration: New duration in minutes (optional)
        agenda: New agenda (optional)
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with success status
    """
    try:
        if not meeting_id:
            return {"success": False, "error": "Meeting ID is required"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_update_meeting")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Prepare update data
        update_data = {}
        if topic:
            update_data["topic"] = topic
        if start_time:
            update_data["start_time"] = start_time
        if duration:
            update_data["duration"] = duration
        if agenda:
            update_data["agenda"] = agenda

        if not update_data:
            return {"success": False, "error": "No update fields provided"}

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session, session.patch(
            f"{ZOOM_API_BASE}/meetings/{meeting_id}", headers=headers, json=update_data
        ) as response:
            if response.status != 204:
                error_data = await response.json()
                logger.error(f"Zoom API error: {error_data}")
                return {
                    "success": False,
                    "error": f"Failed to update meeting: {error_data.get('message', 'Unknown error')}",
                }

            logger.info(f"Successfully updated Zoom meeting: {meeting_id}")

            return {
                "success": True,
                "message": f"Successfully updated meeting {meeting_id}",
                "updated_fields": list(update_data.keys()),
            }

    except Exception as e:
        logger.error(f"Failed to update Zoom meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_zoom_delete_meeting(
    meeting_id: str, config: dict[str, Any] | None = None, runtime_context: Any = None
) -> dict[str, Any]:
    """
    Delete/cancel a Zoom meeting.

    Args:
        meeting_id: Zoom meeting ID
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with success status
    """
    try:
        if not meeting_id:
            return {"success": False, "error": "Meeting ID is required"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_delete_meeting")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{ZOOM_API_BASE}/meetings/{meeting_id}", headers=headers) as response:
                if response.status != 204:
                    error_data = await response.json()
                    logger.error(f"Zoom API error: {error_data}")
                    return {
                        "success": False,
                        "error": f"Failed to delete meeting: {error_data.get('message', 'Unknown error')}",
                    }

                logger.info(f"Successfully deleted Zoom meeting: {meeting_id}")

                return {"success": True, "message": f"Successfully deleted meeting {meeting_id}"}

    except Exception as e:
        logger.error(f"Failed to delete Zoom meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_zoom_get_meeting_recordings(
    meeting_id: str, config: dict[str, Any] | None = None, runtime_context: Any = None
) -> dict[str, Any]:
    """
    Get recordings for a Zoom meeting.

    Args:
        meeting_id: Zoom meeting ID
        config: Configuration dictionary (unused)
        runtime_context: Runtime context for credential resolution

    Returns:
        Dictionary with recording details
    """
    try:
        if not meeting_id:
            return {"success": False, "error": "Meeting ID is required"}

        # Get access token
        if not runtime_context:
            return {"success": False, "error": "No runtime context available"}

        # Create credential resolver
        from src.services.agents.credential_resolver import CredentialResolver

        credential_resolver = CredentialResolver(runtime_context)

        access_token = await credential_resolver.get_zoom_token(tool_name="internal_zoom_get_meeting_recordings")

        if not access_token:
            return {
                "success": False,
                "error": "Zoom authentication expired or not configured. Please reconnect your Zoom account in the OAuth Apps settings.",
            }

        # Make API call
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ZOOM_API_BASE}/meetings/{meeting_id}/recordings", headers=headers) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"Zoom API error: {error_data}")
                    return {
                        "success": False,
                        "error": f"Failed to get recordings: {error_data.get('message', 'Unknown error')}",
                    }

                result = await response.json()
                recordings = result.get("recording_files", [])

                # Format recording data
                formatted_recordings = [
                    {
                        "recording_id": r.get("id"),
                        "meeting_id": r.get("meeting_id"),
                        "recording_start": r.get("recording_start"),
                        "recording_end": r.get("recording_end"),
                        "file_type": r.get("file_type"),
                        "file_size": r.get("file_size"),
                        "download_url": r.get("download_url"),
                        "play_url": r.get("play_url"),
                        "status": r.get("status"),
                    }
                    for r in recordings
                ]

                return {
                    "success": True,
                    "data": {
                        "recordings": formatted_recordings,
                        "total_count": len(formatted_recordings),
                        "meeting_id": meeting_id,
                    },
                    "message": f"Found {len(formatted_recordings)} recordings",
                }

    except Exception as e:
        logger.error(f"Failed to get Zoom meeting recordings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
