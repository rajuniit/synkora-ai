"""Events Tools Registry — PredictHQ and Ticketmaster event discovery."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_events_tools(registry) -> None:
    from src.services.agents.internal_tools.events_tools import (
        internal_get_predicthq_events,
        internal_get_ticketmaster_events,
    )

    async def _phq_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_predicthq_events(
            config=config,
            runtime_context=runtime_context,
            lat=float(kwargs.get("lat", 0.0)),
            lng=float(kwargs.get("lng", 0.0)),
            hours_ahead=int(kwargs.get("hours_ahead", 24)),
            radius_km=float(kwargs.get("radius_km", 5.0)),
        )

    async def _tm_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_ticketmaster_events(
            config=config,
            runtime_context=runtime_context,
            lat=float(kwargs.get("lat", 0.0)),
            lng=float(kwargs.get("lng", 0.0)),
            hours_ahead=int(kwargs.get("hours_ahead", 24)),
            radius_km=float(kwargs.get("radius_km", 5.0)),
        )

    _event_params = {
        "type": "object",
        "properties": {
            "lat": {"type": "number", "description": "Latitude of the search centre"},
            "lng": {"type": "number", "description": "Longitude of the search centre"},
            "hours_ahead": {
                "type": "integer",
                "description": "Forecast window in hours (1–168, default 24)",
            },
            "radius_km": {
                "type": "number",
                "description": "Search radius in kilometres (default 5)",
            },
        },
        "required": ["lat", "lng"],
    }

    registry.register_tool(
        name="internal_get_predicthq_events",
        description=(
            "Fetch upcoming events near a location from PredictHQ. "
            "Returns concerts, sports, festivals, and public events with attendance-based "
            "impact scores and demand multipliers. Requires a PredictHQ OAuth app to be connected."
        ),
        parameters=_event_params,
        function=_phq_wrapper,
    )

    registry.register_tool(
        name="internal_get_ticketmaster_events",
        description=(
            "Fetch upcoming concerts, sports games, and live events near a location from Ticketmaster. "
            "Returns events with venue capacity and demand multipliers. "
            "Requires a Ticketmaster OAuth app to be connected."
        ),
        parameters=_event_params,
        function=_tm_wrapper,
    )

    logger.info("Registered 2 Events tools (PredictHQ + Ticketmaster)")
