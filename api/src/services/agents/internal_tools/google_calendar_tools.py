"""Google Calendar tools for agents."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


async def internal_google_calendar_list_events(
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
    **kwargs,
) -> dict[str, Any]:
    """
    List upcoming calendar events.

    Args:
        time_min: Lower bound for event start time (RFC3339 timestamp or 'now')
        time_max: Upper bound for event start time (RFC3339 timestamp)
        max_results: Maximum number of events to return (default: 10)
        calendar_id: Calendar ID (default: 'primary')

    Returns:
        dict: List of events with summary
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(tool_name="internal_google_calendar_list_events")

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    # Parse time_min
    if time_min == "now" or time_min is None:
        time_min = datetime.now(UTC).isoformat() + "Z"
    elif "Z" not in time_min and "+" not in time_min:
        time_min = time_min + "Z"

    # Parse time_max if provided
    if time_max and "Z" not in time_max and "+" not in time_max:
        time_max = time_max + "Z"

    params = {"timeMin": time_min, "maxResults": max_results, "singleEvents": "true", "orderBy": "startTime"}

    if time_max:
        params["timeMax"] = time_max

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        # Format events for better readability
        events = []
        for item in data.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date"))
            end = item["end"].get("dateTime", item["end"].get("date"))

            events.append(
                {
                    "id": item["id"],
                    "summary": item.get("summary", "No title"),
                    "start": start,
                    "end": end,
                    "location": item.get("location"),
                    "description": item.get("description"),
                    "attendees": [a.get("email") for a in item.get("attendees", [])],
                    "html_link": item.get("htmlLink"),
                }
            )

        return {"success": True, "events": events, "count": len(events)}


async def internal_google_calendar_get_event(event_id: str, calendar_id: str = "primary", **kwargs) -> dict[str, Any]:
    """
    Get details of a specific calendar event.

    Args:
        event_id: Event ID
        calendar_id: Calendar ID (default: 'primary')

    Returns:
        dict: Event details
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(tool_name="internal_google_calendar_get_event")

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        event = response.json()

        return {"success": True, "event": event}


async def internal_google_calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
    send_notifications: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """
    Create a new calendar event.

    Args:
        summary: Event title
        start_time: Start time (RFC3339 timestamp, e.g., '2025-01-15T14:00:00')
        end_time: End time (RFC3339 timestamp)
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
        calendar_id: Calendar ID (default: 'primary')
        send_notifications: Send email notifications to attendees

    Returns:
        dict: Created event details
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_create_event"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    # Ensure timestamps have timezone
    if "Z" not in start_time and "+" not in start_time and "-" not in start_time[-6:]:
        start_time = start_time + "Z"
    if "Z" not in end_time and "+" not in end_time and "-" not in end_time[-6:]:
        end_time = end_time + "Z"

    event_data = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }

    if description:
        event_data["description"] = description

    if location:
        event_data["location"] = location

    if attendees:
        event_data["attendees"] = [{"email": email} for email in attendees]

    params = {"sendUpdates": "all" if send_notifications else "none"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=event_data,
            params=params,
        )
        response.raise_for_status()
        event = response.json()

        return {
            "success": True,
            "event_id": event["id"],
            "html_link": event.get("htmlLink"),
            "message": f"Event '{summary}' created successfully",
        }


async def internal_google_calendar_update_event(
    event_id: str,
    summary: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
    send_notifications: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """
    Update an existing calendar event.

    Args:
        event_id: Event ID to update
        summary: New event title (optional)
        start_time: New start time (optional)
        end_time: New end time (optional)
        description: New description (optional)
        location: New location (optional)
        attendees: New list of attendee emails (optional)
        calendar_id: Calendar ID (default: 'primary')
        send_notifications: Send email notifications to attendees

    Returns:
        dict: Updated event details
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_update_event"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    # First, get the current event
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        event_data = response.json()

    # Update fields
    if summary:
        event_data["summary"] = summary

    if start_time:
        if "Z" not in start_time and "+" not in start_time:
            start_time = start_time + "Z"
        event_data["start"] = {"dateTime": start_time, "timeZone": "UTC"}

    if end_time:
        if "Z" not in end_time and "+" not in end_time:
            end_time = end_time + "Z"
        event_data["end"] = {"dateTime": end_time, "timeZone": "UTC"}

    if description is not None:
        event_data["description"] = description

    if location is not None:
        event_data["location"] = location

    if attendees is not None:
        event_data["attendees"] = [{"email": email} for email in attendees]

    params = {"sendUpdates": "all" if send_notifications else "none"}

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=event_data,
            params=params,
        )
        response.raise_for_status()

        return {"success": True, "message": "Event updated successfully"}


async def internal_google_calendar_delete_event(
    event_id: str, calendar_id: str = "primary", send_notifications: bool = True, **kwargs
) -> dict[str, Any]:
    """
    Delete a calendar event.

    Args:
        event_id: Event ID to delete
        calendar_id: Calendar ID (default: 'primary')
        send_notifications: Send cancellation emails to attendees

    Returns:
        dict: Deletion confirmation
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_delete_event"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    params = {"sendUpdates": "all" if send_notifications else "none"}

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        response.raise_for_status()

        return {"success": True, "message": "Event deleted successfully"}


async def internal_google_calendar_get_free_busy(
    time_min: str, time_max: str, calendars: list[str] | None = None, **kwargs
) -> dict[str, Any]:
    """
    Check free/busy information for calendars.

    Args:
        time_min: Start time for query (RFC3339 timestamp)
        time_max: End time for query (RFC3339 timestamp)
        calendars: List of calendar IDs (default: ['primary'])

    Returns:
        dict: Free/busy information
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_get_free_busy"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    if calendars is None:
        calendars = ["primary"]

    # Ensure timestamps have timezone
    if "Z" not in time_min and "+" not in time_min:
        time_min = time_min + "Z"
    if "Z" not in time_max and "+" not in time_max:
        time_max = time_max + "Z"

    request_data = {"timeMin": time_min, "timeMax": time_max, "items": [{"id": cal_id} for cal_id in calendars]}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CALENDAR_API_BASE}/freeBusy",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=request_data,
        )
        response.raise_for_status()
        data = response.json()

        return {"success": True, "free_busy": data.get("calendars", {})}


async def internal_google_calendar_find_meeting_time(
    attendees: list[str], duration_minutes: int, time_min: str, time_max: str, **kwargs
) -> dict[str, Any]:
    """
    Find available meeting time slots for multiple attendees.

    Args:
        attendees: List of attendee email addresses
        duration_minutes: Meeting duration in minutes
        time_min: Search start time (RFC3339 timestamp)
        time_max: Search end time (RFC3339 timestamp)

    Returns:
        dict: Available time slots
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_find_meeting_time"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    # Get free/busy for all attendees
    result = await internal_google_calendar_get_free_busy(
        time_min=time_min, time_max=time_max, calendars=attendees, runtime_context=runtime_context
    )

    # Parse times
    start = date_parser.parse(time_min if "Z" in time_min else time_min + "Z")
    end = date_parser.parse(time_max if "Z" in time_max else time_max + "Z")
    duration = timedelta(minutes=duration_minutes)

    # Find free slots
    free_slots = []
    current = start

    while current + duration <= end:
        slot_end = current + duration
        is_free = True

        # Check if this slot is free for all attendees
        for _calendar_id, busy_info in result["free_busy"].items():
            for busy_period in busy_info.get("busy", []):
                busy_start = date_parser.parse(busy_period["start"])
                busy_end = date_parser.parse(busy_period["end"])

                # Check for overlap
                if not (slot_end <= busy_start or current >= busy_end):
                    is_free = False
                    break

            if not is_free:
                break

        if is_free:
            free_slots.append({"start": current.isoformat(), "end": slot_end.isoformat()})

        # Move to next slot (30-minute increments)
        current += timedelta(minutes=30)

    return {"success": True, "available_slots": free_slots, "count": len(free_slots)}


async def internal_google_calendar_list_calendars(**kwargs) -> dict[str, Any]:
    """
    List all calendars for the authenticated user.

    Returns:
        dict: List of calendars
    """
    # Get token from runtime_context (same pattern as Zoom tools)
    runtime_context = kwargs.get("runtime_context")

    if not runtime_context:
        return {"success": False, "error": "Runtime context not available. Cannot authenticate with Google Calendar."}

    from src.services.agents.credential_resolver import CredentialResolver

    credential_resolver = CredentialResolver(runtime_context)

    access_token = await credential_resolver.get_google_calendar_token(
        tool_name="internal_google_calendar_list_calendars"
    )

    if not access_token:
        return {
            "success": False,
            "error": "Google Calendar authentication expired or not configured. Please reconnect your Google Calendar account in the OAuth Apps settings.",
        }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/users/me/calendarList", headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()

        calendars = []
        for item in data.get("items", []):
            calendars.append(
                {
                    "id": item["id"],
                    "summary": item.get("summary"),
                    "description": item.get("description"),
                    "primary": item.get("primary", False),
                    "access_role": item.get("accessRole"),
                }
            )

        return {"success": True, "calendars": calendars}
