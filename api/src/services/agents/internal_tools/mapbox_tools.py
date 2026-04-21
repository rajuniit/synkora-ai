"""
Mapbox Tools — generic integration for static maps and directions.

Auth: api_key stored in OAuthApp (provider='mapbox', auth_method='api_token').
All configuration via OAuthApp.config.
"""

import logging
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


async def _get_mapbox_config(runtime_context: Any, tool_name: str) -> dict[str, Any]:
    """Resolve Mapbox credentials from the linked OAuthApp."""
    from sqlalchemy import select

    from src.core.database import get_async_session_factory
    from src.models.agent_tool import AgentTool
    from src.models.oauth_app import OAuthApp
    from src.services.agents.security import decrypt_value

    async with get_async_session_factory()() as db:
        result = await db.execute(
            select(AgentTool).filter(
                AgentTool.agent_id == runtime_context.agent_id,
                AgentTool.tool_name == tool_name,
                AgentTool.enabled,
            )
        )
        agent_tool = result.scalar_one_or_none()
        if not agent_tool or not agent_tool.oauth_app_id:
            raise ValueError(
                f"No OAuth app configured for tool '{tool_name}'. "
                "Please connect a Mapbox OAuth app in Agent Tools settings."
            )

        result = await db.execute(
            select(OAuthApp).filter(
                OAuthApp.id == agent_tool.oauth_app_id,
                OAuthApp.provider.ilike("mapbox"),
                OAuthApp.is_active,
            )
        )
        oauth_app = result.scalar_one_or_none()
        if not oauth_app:
            raise ValueError("No active Mapbox OAuth app found. Check your integrations.")
        if not oauth_app.api_token:
            raise ValueError("Mapbox API key is missing. Edit the OAuth app and add your access token.")

        config = oauth_app.config or {}
        return {
            "access_token": decrypt_value(oauth_app.api_token),
            "style": config.get("style", "mapbox/streets-v12"),
            "timeout": float(config.get("timeout_seconds", 15)),
        }


def _build_static_map_url(
    access_token: str,
    style: str,
    center_lng: float,
    center_lat: float,
    zoom: int,
    width: int,
    height: int,
    markers: list[dict[str, Any]] | None,
    path: list[dict[str, Any]] | None,
) -> str:
    """Construct a Mapbox Static Images API URL."""
    base = f"https://api.mapbox.com/styles/v1/{style}/static"

    overlays = []
    if markers:
        for m in markers[:20]:  # Mapbox overlay limit
            color = (m.get("color") or "f00").lstrip("#")
            label = quote(str(m.get("label", ""))[:2])
            lng = float(m["lng"])
            lat = float(m["lat"])
            pin = f"pin-s-{label}+{color}({lng},{lat})" if label else f"pin-s+{color}({lng},{lat})"
            overlays.append(pin)

    if path and len(path) >= 2:
        coords = ",".join(f"{float(p['lng'])},{float(p['lat'])}" for p in path[:100])
        overlays.append(f"path-3+0074D9-0.8({quote(f'[{coords}]')})")

    overlay_str = ",".join(overlays)
    if overlay_str:
        return f"{base}/{overlay_str}/{center_lng},{center_lat},{zoom}/{width}x{height}?access_token={access_token}"
    return f"{base}/{center_lng},{center_lat},{zoom}/{width}x{height}?access_token={access_token}"


async def internal_get_static_map(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    center_lat: float = 0.0,
    center_lng: float = 0.0,
    zoom: int = 13,
    width: int = 800,
    height: int = 500,
    markers: list[dict[str, Any]] | None = None,
    path: list[dict[str, Any]] | None = None,
    style: str | None = None,
    _resolved_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a Mapbox static map image URL for display in chat.

    Optionally overlay vehicle markers or a route path on the map.
    The returned map_url is a direct image URL that can be rendered inline.

    Args:
        center_lat: Map centre latitude
        center_lng: Map centre longitude
        zoom: Zoom level 0–22 (13 = city block, 15 = street level)
        width: Image width in pixels (max 1280)
        height: Image height in pixels (max 1280)
        markers: List of {lat, lng, label?, color?} — up to 20 markers
        path: List of {lat, lng} ordered coordinates to draw a route line
        style: Mapbox style override (e.g. 'mapbox/satellite-v9'); uses configured default if omitted

    Returns:
        map_url: Static image URL
        embed_url: Interactive Mapbox GL JS embed URL
        center: {lat, lng}
        zoom: effective zoom level
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        cfg = _resolved_cfg or await _get_mapbox_config(runtime_context, "internal_get_static_map")
        token = cfg["access_token"]
        map_style = style or cfg["style"]
        zoom = max(0, min(int(zoom), 22))
        width = max(64, min(int(width), 1280))
        height = max(64, min(int(height), 1280))

        map_url = _build_static_map_url(token, map_style, center_lng, center_lat, zoom, width, height, markers, path)

        # Interactive embed URL (opens in browser/iframe)
        embed_url = (
            f"https://api.mapbox.com/styles/v1/{map_style}.html"
            f"?access_token={token}"
            f"#map={zoom}/{center_lat}/{center_lng}"
        )

        return {
            "success": True,
            "map_url": map_url,
            "embed_url": embed_url,
            "center": {"lat": center_lat, "lng": center_lng},
            "zoom": zoom,
            "marker_count": len(markers) if markers else 0,
        }
    except Exception as e:
        logger.error(f"internal_get_static_map failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_get_directions(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    origin_lat: float = 0.0,
    origin_lng: float = 0.0,
    dest_lat: float = 0.0,
    dest_lng: float = 0.0,
    profile: str = "driving",
    waypoints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Get driving, cycling, or walking directions between two points via Mapbox Directions API.

    Returns route geometry, duration, and distance. Useful for planning ranger routes
    or calculating travel times for rebalancing operations.

    Args:
        origin_lat / origin_lng: Start coordinates
        dest_lat / dest_lng: End coordinates
        profile: Routing profile — 'driving', 'cycling', 'walking' (default: 'driving')
        waypoints: Optional intermediate stops [{lat, lng}]

    Returns:
        distance_km: Route distance in kilometres
        duration_min: Estimated travel time in minutes
        geometry: Encoded route geometry
        steps: Turn-by-turn instructions
        map_url: Static map of the route
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        import httpx

        cfg = await _get_mapbox_config(runtime_context, "internal_get_directions")
        token = cfg["access_token"]
        valid_profiles = {"driving", "cycling", "walking", "driving-traffic"}
        if profile not in valid_profiles:
            profile = "driving"

        # Build coordinate string: origin → waypoints → destination
        coords = [f"{origin_lng},{origin_lat}"]
        for wp in (waypoints or [])[:23]:  # Mapbox limit: 25 total (incl. origin+dest)
            coords.append(f"{float(wp['lng'])},{float(wp['lat'])}")
        coords.append(f"{dest_lng},{dest_lat}")
        coord_str = ";".join(coords)

        url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coord_str}"
        params = {
            "access_token": token,
            "geometries": "geojson",
            "steps": "true",
            "overview": "full",
        }

        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            resp = await client.get(url, params=params)

        if not resp.is_success:
            return {"success": False, "error": f"Mapbox Directions error {resp.status_code}"}

        data = resp.json()
        routes = data.get("routes", [])
        if not routes:
            return {"success": False, "error": "No route found between the given coordinates."}

        route = routes[0]
        distance_km = round(route["distance"] / 1000, 2)
        duration_min = round(route["duration"] / 60, 1)

        # Extract turn-by-turn steps
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                maneuver = step.get("maneuver", {})
                steps.append({
                    "instruction": maneuver.get("instruction", ""),
                    "distance_m": round(step.get("distance", 0)),
                    "duration_s": round(step.get("duration", 0)),
                })

        # Build static map of the route
        route_coords = route.get("geometry", {}).get("coordinates", [])
        path_points = [{"lng": c[0], "lat": c[1]} for c in route_coords[::max(1, len(route_coords) // 50)]]

        mid_lat = (origin_lat + dest_lat) / 2
        mid_lng = (origin_lng + dest_lng) / 2
        map_url_result = await internal_get_static_map(
            config=config,
            runtime_context=runtime_context,
            center_lat=mid_lat,
            center_lng=mid_lng,
            zoom=13,
            width=800,
            height=500,
            markers=[
                {"lat": origin_lat, "lng": origin_lng, "label": "A", "color": "00cc00"},
                {"lat": dest_lat, "lng": dest_lng, "label": "B", "color": "cc0000"},
            ],
            path=path_points,
            _resolved_cfg=cfg,
        )

        return {
            "success": True,
            "profile": profile,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "steps": steps,
            "map_url": map_url_result.get("map_url") if map_url_result.get("success") else None,
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng},
        }
    except Exception as e:
        logger.error(f"internal_get_directions failed: {e}")
        return {"success": False, "error": str(e)}
