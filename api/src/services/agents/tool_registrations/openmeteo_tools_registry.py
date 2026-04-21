"""Open-Meteo Tools Registry — free weather, no API key required."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_openmeteo_tools(registry) -> None:
    from src.services.agents.internal_tools.openmeteo_tools import (
        internal_get_openmeteo_current,
        internal_get_openmeteo_forecast,
    )

    async def _forecast_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_openmeteo_forecast(
            config=config,
            runtime_context=runtime_context,
            lat=float(kwargs.get("lat", 0.0)),
            lng=float(kwargs.get("lng", 0.0)),
            hours_ahead=int(kwargs.get("hours_ahead", 24)),
        )

    async def _current_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_openmeteo_current(
            config=config,
            runtime_context=runtime_context,
            lat=float(kwargs.get("lat", 0.0)),
            lng=float(kwargs.get("lng", 0.0)),
        )

    registry.register_tool(
        name="internal_get_openmeteo_forecast",
        description=(
            "Get hourly weather forecast for any location using Open-Meteo (free, no API key needed). "
            "Returns temperature, precipitation probability, wind speed, and a demand_modifier "
            "(0.0–2.0) indicating how weather affects outdoor activity levels. "
            "Use this when OpenWeather is not configured or as a free alternative."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lng": {"type": "number", "description": "Longitude"},
                "hours_ahead": {
                    "type": "integer",
                    "description": "Number of hours to forecast (1–48, default 24)",
                },
            },
            "required": ["lat", "lng"],
        },
        function=_forecast_wrapper,
    )

    registry.register_tool(
        name="internal_get_openmeteo_current",
        description=(
            "Get current weather conditions for any location using Open-Meteo (free, no API key needed). "
            "Returns temperature, description, wind speed, humidity, and a demand_modifier. "
            "Use this when OpenWeather is not configured or as a free alternative."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lng": {"type": "number", "description": "Longitude"},
            },
            "required": ["lat", "lng"],
        },
        function=_current_wrapper,
    )

    logger.info("Registered 2 Open-Meteo tools (no API key required)")
