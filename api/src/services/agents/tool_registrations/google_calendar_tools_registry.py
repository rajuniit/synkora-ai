"""
Google Calendar Tools Registry

Registers all Google Calendar-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_google_calendar_tools(registry):
    """
    Register all Google Calendar tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.google_calendar_tools import (
        internal_google_calendar_create_event,
        internal_google_calendar_delete_event,
        internal_google_calendar_find_meeting_time,
        internal_google_calendar_get_event,
        internal_google_calendar_get_free_busy,
        internal_google_calendar_list_calendars,
        internal_google_calendar_list_events,
        internal_google_calendar_update_event,
    )

    # Google Calendar tools - create wrappers that inject runtime_context
    async def google_calendar_list_events_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_list_events(
            time_min=kwargs.get("time_min"),
            time_max=kwargs.get("time_max"),
            max_results=kwargs.get("max_results", 10),
            calendar_id=kwargs.get("calendar_id", "primary"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_get_event_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_get_event(
            event_id=kwargs.get("event_id"),
            calendar_id=kwargs.get("calendar_id", "primary"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_create_event_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_create_event(
            summary=kwargs.get("summary"),
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            description=kwargs.get("description"),
            location=kwargs.get("location"),
            attendees=kwargs.get("attendees"),
            calendar_id=kwargs.get("calendar_id", "primary"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_update_event_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_update_event(
            event_id=kwargs.get("event_id"),
            summary=kwargs.get("summary"),
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            description=kwargs.get("description"),
            location=kwargs.get("location"),
            attendees=kwargs.get("attendees"),
            calendar_id=kwargs.get("calendar_id", "primary"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_delete_event_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_delete_event(
            event_id=kwargs.get("event_id"),
            calendar_id=kwargs.get("calendar_id", "primary"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_get_free_busy_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_get_free_busy(
            time_min=kwargs.get("time_min"),
            time_max=kwargs.get("time_max"),
            calendars=kwargs.get("calendars", ["primary"]),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_find_meeting_time_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_find_meeting_time(
            attendees=kwargs.get("attendees", []),
            duration_minutes=kwargs.get("duration_minutes", 60),
            time_min=kwargs.get("time_min"),
            time_max=kwargs.get("time_max"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_calendar_list_calendars_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_calendar_list_calendars(config=config, runtime_context=runtime_context)

    # Register all Google Calendar tools
    registry.register_tool(
        name="internal_google_calendar_list_events",
        description="List events from Google Calendar. Returns events within specified time range.",
        parameters={
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "Start time in ISO 8601 format (optional)"},
                "time_max": {"type": "string", "description": "End time in ISO 8601 format (optional)"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum events to return (default: 10)",
                    "default": 10,
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
            },
            "required": [],
        },
        function=google_calendar_list_events_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_get_event",
        description="Get details of a specific calendar event.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event ID"},
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
            },
            "required": ["event_id"],
        },
        function=google_calendar_get_event_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_create_event",
        description="Create a new Google Calendar event. Schedule meetings with attendees.",
        parameters={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title/summary"},
                "start_time": {"type": "string", "description": "Start time in ISO 8601 format"},
                "end_time": {"type": "string", "description": "End time in ISO 8601 format"},
                "description": {"type": "string", "description": "Event description (optional)"},
                "location": {"type": "string", "description": "Event location (optional)"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses (optional)",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
            },
            "required": ["summary", "start_time", "end_time"],
        },
        function=google_calendar_create_event_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_update_event",
        description="Update an existing calendar event.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event ID to update"},
                "summary": {"type": "string", "description": "New event title (optional)"},
                "start_time": {"type": "string", "description": "New start time in ISO 8601 format (optional)"},
                "end_time": {"type": "string", "description": "New end time in ISO 8601 format (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
                "location": {"type": "string", "description": "New location (optional)"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New attendee list (optional)",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
            },
            "required": ["event_id"],
        },
        function=google_calendar_update_event_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_delete_event",
        description="Delete a calendar event.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event ID to delete"},
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
            },
            "required": ["event_id"],
        },
        function=google_calendar_delete_event_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_get_free_busy",
        description="Check availability (free/busy) for calendars.",
        parameters={
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "Start time in ISO 8601 format"},
                "time_max": {"type": "string", "description": "End time in ISO 8601 format"},
                "calendars": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of calendar IDs or email addresses",
                    "default": ["primary"],
                },
            },
            "required": ["time_min", "time_max"],
        },
        function=google_calendar_get_free_busy_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_find_meeting_time",
        description="Find available meeting slots for attendees.",
        parameters={
            "type": "object",
            "properties": {
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Meeting duration in minutes (default: 60)",
                    "default": 60,
                },
                "time_min": {"type": "string", "description": "Search start time in ISO 8601 format (optional)"},
                "time_max": {"type": "string", "description": "Search end time in ISO 8601 format (optional)"},
            },
            "required": [],
        },
        function=google_calendar_find_meeting_time_wrapper,
        requires_auth="google_calendar",
    )

    registry.register_tool(
        name="internal_google_calendar_list_calendars",
        description="List all calendars available to the user.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=google_calendar_list_calendars_wrapper,
        requires_auth="google_calendar",
    )

    logger.info("Registered 8 Google Calendar tools")
