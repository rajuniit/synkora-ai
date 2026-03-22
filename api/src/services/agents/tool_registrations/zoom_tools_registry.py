"""
Zoom Tools Registry

Registers all Zoom-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_zoom_tools(registry):
    """
    Register all Zoom tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.zoom_tools import (
        internal_zoom_create_meeting,
        internal_zoom_delete_meeting,
        internal_zoom_get_meeting,
        internal_zoom_get_meeting_recordings,
        internal_zoom_list_meetings,
        internal_zoom_update_meeting,
    )

    # Zoom tools - create wrappers that inject runtime_context
    async def internal_zoom_create_meeting_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_create_meeting(
            topic=kwargs.get("topic"),
            start_time=kwargs.get("start_time"),
            duration=kwargs.get("duration"),
            timezone=kwargs.get("timezone", "UTC"),
            agenda=kwargs.get("agenda"),
            password=kwargs.get("password"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_zoom_list_meetings_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_list_meetings(
            meeting_type=kwargs.get("meeting_type", "scheduled"),
            page_size=kwargs.get("page_size", 30),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_zoom_get_meeting_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_get_meeting(
            meeting_id=kwargs.get("meeting_id"), config=config, runtime_context=runtime_context
        )

    async def internal_zoom_update_meeting_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_update_meeting(
            meeting_id=kwargs.get("meeting_id"),
            topic=kwargs.get("topic"),
            start_time=kwargs.get("start_time"),
            duration=kwargs.get("duration"),
            agenda=kwargs.get("agenda"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_zoom_delete_meeting_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_delete_meeting(
            meeting_id=kwargs.get("meeting_id"), config=config, runtime_context=runtime_context
        )

    async def internal_zoom_get_meeting_recordings_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_zoom_get_meeting_recordings(
            meeting_id=kwargs.get("meeting_id"), config=config, runtime_context=runtime_context
        )

    # Register all Zoom tools
    registry.register_tool(
        name="internal_zoom_create_meeting",
        description="Create a new Zoom meeting. Schedule meetings with specific topics, times, and durations. Returns meeting ID, join URL, and password.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Meeting topic/title"},
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (e.g., '2025-01-10T10:00:00Z')",
                },
                "duration": {"type": "integer", "description": "Duration in minutes"},
                "timezone": {"type": "string", "description": "Timezone (default: UTC)", "default": "UTC"},
                "agenda": {"type": "string", "description": "Meeting agenda/description (optional)"},
                "password": {"type": "string", "description": "Meeting password (optional)"},
            },
            "required": ["topic", "start_time", "duration"],
        },
        function=internal_zoom_create_meeting_wrapper,
        requires_auth="zoom",
    )

    registry.register_tool(
        name="internal_zoom_list_meetings",
        description="List user's Zoom meetings. Returns list of scheduled, live, or upcoming meetings with details.",
        parameters={
            "type": "object",
            "properties": {
                "meeting_type": {
                    "type": "string",
                    "description": "Type of meetings to list",
                    "enum": ["scheduled", "live", "upcoming"],
                    "default": "scheduled",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of meetings to return (max 300)",
                    "default": 30,
                },
            },
            "required": [],
        },
        function=internal_zoom_list_meetings_wrapper,
        requires_auth="zoom",
    )

    registry.register_tool(
        name="internal_zoom_get_meeting",
        description="Get details of a specific Zoom meeting. Returns comprehensive meeting information including join URL, password, and settings.",
        parameters={
            "type": "object",
            "properties": {"meeting_id": {"type": "string", "description": "Zoom meeting ID"}},
            "required": ["meeting_id"],
        },
        function=internal_zoom_get_meeting_wrapper,
        requires_auth="zoom",
    )

    registry.register_tool(
        name="internal_zoom_update_meeting",
        description="Update a Zoom meeting's details. Can change topic, start time, duration, or agenda.",
        parameters={
            "type": "object",
            "properties": {
                "meeting_id": {"type": "string", "description": "Zoom meeting ID"},
                "topic": {"type": "string", "description": "New meeting topic (optional)"},
                "start_time": {"type": "string", "description": "New start time in ISO 8601 format (optional)"},
                "duration": {"type": "integer", "description": "New duration in minutes (optional)"},
                "agenda": {"type": "string", "description": "New agenda (optional)"},
            },
            "required": ["meeting_id"],
        },
        function=internal_zoom_update_meeting_wrapper,
        requires_auth="zoom",
    )

    registry.register_tool(
        name="internal_zoom_delete_meeting",
        description="Delete/cancel a Zoom meeting. Permanently removes the meeting from the schedule.",
        parameters={
            "type": "object",
            "properties": {"meeting_id": {"type": "string", "description": "Zoom meeting ID"}},
            "required": ["meeting_id"],
        },
        function=internal_zoom_delete_meeting_wrapper,
        requires_auth="zoom",
    )

    registry.register_tool(
        name="internal_zoom_get_meeting_recordings",
        description="Get recordings for a Zoom meeting. Returns list of recording files with download and play URLs.",
        parameters={
            "type": "object",
            "properties": {"meeting_id": {"type": "string", "description": "Zoom meeting ID"}},
            "required": ["meeting_id"],
        },
        function=internal_zoom_get_meeting_recordings_wrapper,
        requires_auth="zoom",
    )

    logger.info("Registered 6 Zoom tools")
