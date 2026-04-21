"""
Events Tools — generic integration for nearby event discovery.

Supports two independent providers (configure either or both via OAuth Apps):
  - PredictHQ  (provider='predicthq')   — primary; attendance-based impact scores
  - Ticketmaster (provider='ticketmaster') — concerts, sports, live events

Both tools are independently LLM-callable and share helper logic for
demand multiplier computation and result normalisation.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def _get_provider_config(runtime_context: Any, tool_name: str, provider: str) -> dict[str, Any] | None:
    """Return decrypted config for a provider linked to the given tool, or None if not configured."""
    from src.core.database import get_async_session_factory
    from src.models.agent_tool import AgentTool
    from src.models.oauth_app import OAuthApp
    from src.services.agents.security import decrypt_value
    from sqlalchemy import select

    try:
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
                return None

            result = await db.execute(
                select(OAuthApp).filter(
                    OAuthApp.id == agent_tool.oauth_app_id,
                    OAuthApp.provider.ilike(provider),
                    OAuthApp.is_active,
                )
            )
            oauth_app = result.scalar_one_or_none()
            if not oauth_app or not oauth_app.api_token:
                return None

            config = oauth_app.config or {}
            return {
                "api_key": decrypt_value(oauth_app.api_token),
                "base_url": config.get("base_url", _default_base_url(provider)),
                "timeout": float(config.get("timeout_seconds", 15)),
                "impact_weight": float(config.get("impact_weight", 0.30)),
                "max_radius_km": float(config.get("max_radius_km", 10)),
                "categories": config.get("categories"),
            }
    except Exception as e:
        logger.warning(f"Failed to load {provider} config: {e}")
        return None


def _default_base_url(provider: str) -> str:
    defaults = {
        "predicthq": "https://api.predicthq.com",
        "ticketmaster": "https://app.ticketmaster.com",
    }
    return defaults.get(provider.lower(), "")


def _impact_to_multiplier(impact_score: float, weight: float = 0.30) -> float:
    return 1.0 + (impact_score / 100.0) * (weight * 10)


def _build_event_result(events: list[dict[str, Any]], source_label: str) -> dict[str, Any]:
    if not events:
        return {
            "success": True,
            "events": [],
            "peak_multiplier": 1.0,
            "combined_multiplier": 1.0,
            "has_major_event": False,
            "summary": f"No significant events found nearby ({source_label})",
        }

    peak = max(ev["demand_multiplier"] for ev in events)
    combined = min(sum(ev["demand_multiplier"] - 1 for ev in events) + 1, 4.0)
    has_major = any(ev["impact_score"] >= 60 for ev in events)
    top = events[0]
    summary = (
        f"{len(events)} event(s) nearby — top: '{top['name']}' "
        f"({top['category']}) with {top['impact_score']:.0f}/100 impact"
    )
    return {
        "success": True,
        "events": events,
        "peak_multiplier": round(peak, 2),
        "combined_multiplier": round(combined, 2),
        "has_major_event": has_major,
        "summary": summary,
    }


async def internal_get_predicthq_events(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lat: float = 0.0,
    lng: float = 0.0,
    hours_ahead: int = 24,
    radius_km: float = 5.0,
) -> dict[str, Any]:
    """
    Fetch upcoming events near a location from PredictHQ.

    Returns events with attendance-based impact scores and demand multipliers.
    Configure by linking a PredictHQ OAuth app to this tool in Agent Tools settings.

    Args:
        lat: Latitude of the search centre
        lng: Longitude of the search centre
        hours_ahead: Forecast window in hours (1–168)
        radius_km: Search radius in kilometres (default 5)

    Returns:
        events: list of events with name, category, start_iso, venue, attendance, impact_score, demand_multiplier
        peak_multiplier: highest single-event multiplier
        combined_multiplier: additive combination capped at 4.0
        has_major_event: true if any event has impact_score >= 60
        summary: human-readable description
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        cfg = await _get_provider_config(runtime_context, "internal_get_predicthq_events", "predicthq")
        if not cfg:
            return {"success": False, "error": "PredictHQ not configured. Connect a PredictHQ OAuth app in Agent Tools."}

        hours_ahead = max(1, min(int(hours_ahead), 168))
        now = datetime.now(tz=UTC)
        end_dt = now + timedelta(hours=hours_ahead)
        effective_radius = float(radius_km) if radius_km else cfg["max_radius_km"]

        url = f"{cfg['base_url'].rstrip('/')}/v1/events/"
        headers = {"Authorization": f"Bearer {cfg['api_key']}", "Accept": "application/json"}
        params: dict[str, Any] = {
            "within": f"{effective_radius}km@{lat},{lng}",
            "start.gte": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "start.lte": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "sort": "-phq_attendance",
            "limit": 50,
        }
        if cfg.get("categories"):
            params["category"] = ",".join(cfg["categories"])

        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            resp = await client.get(url, headers=headers, params=params)

        if not resp.is_success:
            return {"success": False, "error": f"PredictHQ API error {resp.status_code}: {resp.text[:200]}"}

        events = []
        for ev in resp.json().get("results", []):
            impact = float(ev.get("phq_attendance", 0) or 0)
            impact_score = min(impact / 1000, 100)
            events.append({
                "source": "predicthq",
                "id": ev.get("id", ""),
                "name": ev.get("title", ""),
                "category": ev.get("category", ""),
                "start_iso": ev.get("start", ""),
                "end_iso": ev.get("end", ""),
                "venue": (ev.get("entities") or [{}])[0].get("name", ""),
                "attendance": int(impact),
                "impact_score": round(impact_score, 1),
                "demand_multiplier": round(_impact_to_multiplier(impact_score, cfg["impact_weight"]), 2),
            })

        events.sort(key=lambda e: e["impact_score"], reverse=True)
        return _build_event_result(events, "PredictHQ")

    except Exception as e:
        logger.error(f"internal_get_predicthq_events failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_get_ticketmaster_events(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lat: float = 0.0,
    lng: float = 0.0,
    hours_ahead: int = 24,
    radius_km: float = 5.0,
) -> dict[str, Any]:
    """
    Fetch upcoming events near a location from Ticketmaster.

    Returns concerts, sports games, and live events with demand multipliers.
    Configure by linking a Ticketmaster OAuth app to this tool in Agent Tools settings.

    Args:
        lat: Latitude of the search centre
        lng: Longitude of the search centre
        hours_ahead: Forecast window in hours (1–168)
        radius_km: Search radius in kilometres (default 5)

    Returns:
        events: list of events with name, category, start_iso, venue, attendance, impact_score, demand_multiplier
        peak_multiplier: highest single-event multiplier
        combined_multiplier: additive combination capped at 4.0
        has_major_event: true if any event has impact_score >= 60
        summary: human-readable description
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        cfg = await _get_provider_config(runtime_context, "internal_get_ticketmaster_events", "ticketmaster")
        if not cfg:
            return {"success": False, "error": "Ticketmaster not configured. Connect a Ticketmaster OAuth app in Agent Tools."}

        hours_ahead = max(1, min(int(hours_ahead), 168))
        now = datetime.now(tz=UTC)
        end_dt = now + timedelta(hours=hours_ahead)
        effective_radius = float(radius_km) if radius_km else cfg["max_radius_km"]

        url = f"{cfg['base_url'].rstrip('/')}/discovery/v2/events.json"
        params: dict[str, Any] = {
            "apikey": cfg["api_key"],
            "latlong": f"{lat},{lng}",
            "radius": effective_radius,
            "unit": "km",
            "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "size": 50,
            "sort": "relevance,desc",
        }

        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            resp = await client.get(url, params=params)

        if not resp.is_success:
            return {"success": False, "error": f"Ticketmaster API error {resp.status_code}: {resp.text[:200]}"}

        events_raw = resp.json().get("_embedded", {}).get("events", [])
        events = []
        for ev in events_raw:
            venue_data = (ev.get("_embedded") or {}).get("venues", [{}])[0]
            general_rule = (venue_data.get("generalInfo") or {}).get("generalRule", "") or ""
            attendance_str = general_rule.split()[0].replace(",", "") if general_rule.split() else "0"
            try:
                attendance = int(attendance_str)
            except ValueError:
                attendance = 0
            impact_score = min(attendance / 1000, 100) if attendance else 30
            segment_name = ""
            if ev.get("classifications"):
                segment_name = (ev["classifications"][0].get("segment") or {}).get("name", "")

            events.append({
                "source": "ticketmaster",
                "id": ev.get("id", ""),
                "name": ev.get("name", ""),
                "category": segment_name or ev.get("type", ""),
                "start_iso": (ev.get("dates") or {}).get("start", {}).get("dateTime", ""),
                "end_iso": "",
                "venue": venue_data.get("name", ""),
                "attendance": attendance,
                "impact_score": round(impact_score, 1),
                "demand_multiplier": round(_impact_to_multiplier(impact_score, cfg["impact_weight"]), 2),
            })

        events.sort(key=lambda e: e["impact_score"], reverse=True)
        return _build_event_result(events, "Ticketmaster")

    except Exception as e:
        logger.error(f"internal_get_ticketmaster_events failed: {e}")
        return {"success": False, "error": str(e)}
