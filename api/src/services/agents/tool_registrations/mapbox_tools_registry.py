"""Mapbox Tools Registry — static maps and directions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_mapbox_tools(registry) -> None:
    from src.services.agents.internal_tools.mapbox_tools import (
        internal_get_directions,
        internal_get_static_map,
    )

    async def _map_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_static_map(
            config=config,
            runtime_context=runtime_context,
            center_lat=float(kwargs.get("center_lat", 0.0)),
            center_lng=float(kwargs.get("center_lng", 0.0)),
            zoom=int(kwargs.get("zoom", 13)),
            width=int(kwargs.get("width", 800)),
            height=int(kwargs.get("height", 500)),
            markers=kwargs.get("markers"),
            path=kwargs.get("path"),
            style=kwargs.get("style"),
        )

    async def _directions_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_directions(
            config=config,
            runtime_context=runtime_context,
            origin_lat=float(kwargs.get("origin_lat", 0.0)),
            origin_lng=float(kwargs.get("origin_lng", 0.0)),
            dest_lat=float(kwargs.get("dest_lat", 0.0)),
            dest_lng=float(kwargs.get("dest_lng", 0.0)),
            profile=kwargs.get("profile", "driving"),
            waypoints=kwargs.get("waypoints"),
        )

    registry.register_tool(
        name="internal_get_static_map",
        description=(
            "Generate a Mapbox static map image URL showing a location with optional vehicle markers and route paths. "
            "The returned map_url is a direct image that renders inline in the chat. "
            "Use for displaying fleet locations, zones, or rebalancing routes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "center_lat": {"type": "number", "description": "Map centre latitude"},
                "center_lng": {"type": "number", "description": "Map centre longitude"},
                "zoom": {
                    "type": "integer",
                    "description": "Zoom level 0–22 (13=city block, 15=street; default 13)",
                },
                "width": {"type": "integer", "description": "Image width in pixels (default 800, max 1280)"},
                "height": {"type": "integer", "description": "Image height in pixels (default 500, max 1280)"},
                "markers": {
                    "type": "array",
                    "description": "Vehicle or point markers to overlay. Each item: {lat, lng, label?, color?}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lng": {"type": "number"},
                            "label": {"type": "string", "description": "1–2 char label (e.g. 'A', '1')"},
                            "color": {"type": "string", "description": "Hex colour without # (e.g. 'ff0000')"},
                        },
                        "required": ["lat", "lng"],
                    },
                },
                "path": {
                    "type": "array",
                    "description": "Ordered route coordinates to draw as a line. Each item: {lat, lng}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lng": {"type": "number"},
                        },
                        "required": ["lat", "lng"],
                    },
                },
                "style": {
                    "type": "string",
                    "description": "Mapbox style ID (e.g. 'mapbox/streets-v12', 'mapbox/satellite-v9')",
                },
            },
            "required": ["center_lat", "center_lng"],
        },
        function=_map_wrapper,
    )

    registry.register_tool(
        name="internal_get_directions",
        description=(
            "Get turn-by-turn directions between two points using Mapbox Directions API. "
            "Returns route distance, duration, step-by-step instructions, and a static map URL showing the route. "
            "Useful for planning ranger routes or calculating rebalancing travel times."
        ),
        parameters={
            "type": "object",
            "properties": {
                "origin_lat": {"type": "number", "description": "Start latitude"},
                "origin_lng": {"type": "number", "description": "Start longitude"},
                "dest_lat": {"type": "number", "description": "End latitude"},
                "dest_lng": {"type": "number", "description": "End longitude"},
                "profile": {
                    "type": "string",
                    "description": "Routing profile: 'driving', 'cycling', 'walking' (default: 'driving')",
                },
                "waypoints": {
                    "type": "array",
                    "description": "Optional intermediate stops. Each item: {lat, lng}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lng": {"type": "number"},
                        },
                        "required": ["lat", "lng"],
                    },
                },
            },
            "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
        },
        function=_directions_wrapper,
    )

    logger.info("Registered 2 Mapbox tools")
