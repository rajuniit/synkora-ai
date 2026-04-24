"""
Micromobility Intelligence Tools.

Pre-computes analytical insights from Micromobility fleet data so the LLM receives
structured results rather than raw JSON dumps. Each tool fetches data from the
Micromobility API, applies Python-level computation, and returns clean, actionable output.

The LLM calls these tools instead of (or after) the raw micromobility tools when
the question requires cross-vehicle analysis, demand prediction, or rebalancing plans.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Thresholds — configurable via OAuthApp.config on the micromobility OAuth app
_DEFAULT_LOW_BATTERY_PCT = 20
_DEFAULT_IDLE_HOURS = 4
_REBALANCE_MIN_SURPLUS = 2  # min extra vehicles before suggesting a move


async def _fetch_all_vehicles(
    runtime_context: Any, config: Any, _meta_out: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Fetch all vehicles from Micromobility with pagination. Always filters bike_category=P."""
    from src.services.agents.internal_tools.micromobility_tools import internal_micromobility_list_vehicles

    all_vehicles: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    while True:
        resp = await internal_micromobility_list_vehicles(
            config=config,
            runtime_context=runtime_context,
            bike_category="P",  # always fetch real (non-test) bike category
            limit=page_size,
            offset=offset,
        )
        if not isinstance(resp, dict) or not resp.get("success"):
            break
        items = resp.get("vehicles") or []
        # Capture meta from first page (has total count + fleet-wide summary)
        if _meta_out is not None and offset == 0:
            _meta_out.update(resp.get("meta") or {})
            _meta_out["api_summary"] = resp.get("summary") or {}
            _meta_out["total_count"] = resp.get("count")
        if not items:
            logger.info(f"[fetch_all_vehicles] page offset={offset} returned 0 items — stopping")
            break
        logger.info(
            f"[fetch_all_vehicles] page offset={offset} got {len(items)} vehicles (total so far: {len(all_vehicles) + len(items)})"
        )
        all_vehicles.extend(items)
        if len(items) < page_size:
            logger.info(
                f"[fetch_all_vehicles] last page (got {len(items)} < {page_size}) — done, total={len(all_vehicles)}"
            )
            break
        offset += page_size
        if offset > 2000:
            logger.warning(f"[fetch_all_vehicles] hit 2000 offset cap — stopping, total={len(all_vehicles)}")
            break
    logger.info(f"[fetch_all_vehicles] final total vehicles fetched: {len(all_vehicles)}")
    return all_vehicles


async def _fetch_all_trips(runtime_context: Any, config: Any, **filters) -> list[dict[str, Any]]:
    """Fetch trips with optional filters."""
    from src.services.agents.internal_tools.micromobility_tools import internal_micromobility_list_trips

    all_trips: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    while True:
        resp = await internal_micromobility_list_trips(
            config=config, runtime_context=runtime_context, limit=page_size, offset=offset, **filters
        )
        if not isinstance(resp, dict) or not resp.get("success"):
            break
        # list_trips normalizes response: items available at resp["trips"]
        items = resp.get("trips") or []
        if not items:
            logger.info(f"[fetch_all_trips] page offset={offset} returned 0 items — stopping")
            break
        logger.info(
            f"[fetch_all_trips] page offset={offset} got {len(items)} trips (total so far: {len(all_trips) + len(items)})"
        )
        all_trips.extend(items)
        if len(items) < page_size:
            logger.info(f"[fetch_all_trips] last page (got {len(items)} < {page_size}) — done, total={len(all_trips)}")
            break
        offset += page_size
        if offset > 1000:
            logger.warning(f"[fetch_all_trips] hit 1000 offset cap — stopping, total={len(all_trips)}")
            break
    logger.info(f"[fetch_all_trips] final total trips fetched: {len(all_trips)} | filters={filters}")
    return all_trips


def _hours_since(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        ts = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(tz=UTC) - ts
        return delta.total_seconds() / 3600
    except Exception:
        return None


async def internal_micromobility_get_fleet_health(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    low_battery_threshold: int = _DEFAULT_LOW_BATTERY_PCT,
    idle_hours_threshold: int = _DEFAULT_IDLE_HOURS,
) -> dict[str, Any]:
    """
    Analyse the overall health of the fleet: battery levels, idle vehicles, and maintenance.

    Fetches all vehicles and computes:
    - Low-battery vehicles (below threshold)
    - Idle vehicles (no trip for N hours)
    - Vehicles in maintenance
    - KPI summary: operational rate, avg battery, availability

    Args:
        low_battery_threshold: Battery % below which a vehicle is flagged (default 20%)
        idle_hours_threshold: Hours since last trip before vehicle is considered idle (default 4h)

    Returns:
        summary: KPI object with totals and rates
        low_battery: list of {vehicle_id, battery_pct, zone, lat, lng}
        idle: list of {vehicle_id, idle_hours, zone, lat, lng}
        maintenance: list of {vehicle_id, zone}
        recommended_actions: prioritised list of action strings
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        meta_out: dict[str, Any] = {}
        vehicles = await _fetch_all_vehicles(runtime_context, config, _meta_out=meta_out)
        if not vehicles:
            return {"success": False, "error": "No vehicle data returned from Micromobility API."}

        # Use API-provided summary (covers all pages, pre-computed server-side)
        api_summary = meta_out.get("api_summary") or {}
        total = meta_out.get("total_count") or len(vehicles)

        low_battery: list[dict[str, Any]] = []
        idle_vehicles: list[dict[str, Any]] = []
        maintenance_vehicles: list[dict[str, Any]] = []
        batteries: list[float] = []

        for v in vehicles:
            vid = v.get("qr_code") or v.get("name") or v.get("id") or ""

            # Micromobility nested flag dicts
            _sf = v.get("status_flags") or {}
            _of = v.get("operational_flags") or {}
            _gf = v.get("general_flags") or {}

            is_on_ride = bool(_sf.get("is_on_ride"))
            is_idle = bool(_sf.get("is_idle"))
            is_in_maintenance = bool(_of.get("maintenance"))
            flag_low_battery = bool(_gf.get("low_battery"))

            # Zone from nested fleet object
            _fleet = v.get("fleet") or {}
            zone = _fleet.get("name") or _fleet.get("id") or "Unknown"

            # Location: "lat,lng" string
            loc_raw = v.get("location")
            lat: str | None = None
            lng: str | None = None
            if isinstance(loc_raw, str) and "," in loc_raw:
                parts = loc_raw.split(",", 1)
                lat, lng = parts[0].strip(), parts[1].strip()

            # Battery from lock.power_level (e.g. "96.00")
            _lock = v.get("lock") or {}
            battery_raw = _lock.get("power_level")
            battery: float | None = None
            try:
                battery = float(battery_raw) if battery_raw is not None else None
            except (ValueError, TypeError):
                pass

            if battery is not None:
                batteries.append(battery)

            # Low battery: use API flag OR threshold check on lock power level
            if (flag_low_battery or (battery is not None and battery < low_battery_threshold)) and not is_on_ride:
                low_battery.append(
                    {
                        "qr_code": vid,
                        "battery_pct": battery,
                        "service_area": zone,
                        "lat": lat,
                        "lng": lng,
                    }
                )

            if is_in_maintenance:
                maintenance_vehicles.append({"qr_code": vid, "service_area": zone})
            elif not is_on_ride:
                last_seen_ts = v.get("last_connected_at") or v.get("last_loc_updated_at")
                idle_h = _hours_since(last_seen_ts)
                if is_idle or (idle_h is not None and idle_h >= idle_hours_threshold):
                    idle_vehicles.append(
                        {
                            "qr_code": vid,
                            "battery_pct": battery,
                            "idle_hours": round(idle_h, 1) if idle_h is not None else None,
                            "no_heartbeat": not bool(v.get("heart_beat")),
                            "service_area": zone,
                            "lat": lat,
                            "lng": lng,
                        }
                    )

        avg_battery = round(sum(batteries) / len(batteries), 1) if batteries else None
        low_battery.sort(key=lambda x: x.get("battery_pct") or 100)
        idle_vehicles.sort(key=lambda x: x.get("idle_hours") or 0, reverse=True)

        # Fleet-wide counts from API summary (accurate across all pages)
        api_idle = api_summary.get("idle", len(idle_vehicles))
        api_low_bat = api_summary.get("low_battery", len(low_battery))
        api_maintenance = api_summary.get("maintenance", len(maintenance_vehicles))
        api_on_ride = api_summary.get("on_ride", 0)
        operational = total - api_maintenance - api_idle
        operational_rate = round(max(operational, 0) / total * 100, 1) if total else 0

        actions = []
        if api_low_bat:
            top = low_battery[0] if low_battery else {}
            actions.append(
                f"Dispatch rangers to charge {api_low_bat} low-battery vehicle(s)"
                + (f" — priority: {top.get('qr_code')} at {top.get('battery_pct')}%" if top else "")
            )
        if api_summary.get("iot_fault"):
            actions.append(f"{api_summary['iot_fault']} vehicle(s) with IoT fault — investigate connectivity")
        if api_summary.get("geofence_alert"):
            actions.append(f"{api_summary['geofence_alert']} vehicle(s) outside geofence — review positions")
        if api_summary.get("illegally_parking"):
            actions.append(
                f"{api_summary['illegally_parking']} vehicle(s) illegally parked — dispatch ranger to relocate"
            )
        if api_summary.get("rebalance"):
            actions.append(f"{api_summary['rebalance']} vehicle(s) flagged for rebalancing")
        if api_summary.get("charging_pick"):
            actions.append(f"{api_summary['charging_pick']} vehicle(s) need charging pickup")
        if api_maintenance:
            actions.append(f"{api_maintenance} vehicle(s) in maintenance — review completion status")
        if not actions:
            actions.append("Fleet is in good health — no immediate actions required")

        return {
            "success": True,
            "summary": {
                "total_vehicles": total,
                "on_ride": api_on_ride,
                "idle": api_idle,
                "operational": operational,
                "operational_rate_pct": operational_rate,
                "avg_battery_pct": avg_battery,
                "low_battery_count": api_low_bat,
                "on_charging": api_summary.get("on_charging", 0),
                "parking": api_summary.get("parking", 0),
                "illegally_parking": api_summary.get("illegally_parking", 0),
                "iot_fault": api_summary.get("iot_fault", 0),
                "geofence_alert": api_summary.get("geofence_alert", 0),
                "rebalance": api_summary.get("rebalance", 0),
                "charging_pick": api_summary.get("charging_pick", 0),
                "maintenance_count": api_maintenance,
                "percentages": api_summary.get("percentages") or {},
                "thresholds": {"low_battery_pct": low_battery_threshold, "idle_hours": idle_hours_threshold},
            },
            "low_battery": low_battery[:20],
            "idle": idle_vehicles[:20],
            "maintenance": maintenance_vehicles[:20],
            "recommended_actions": actions,
        }
    except Exception as e:
        logger.error(f"internal_micromobility_get_fleet_health failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_zone_demand_supply(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """
    Compare current vehicle supply vs historical trip demand per service zone.

    Uses the last N days of trip data to compute average trips per zone per day,
    then compares with the current number of available vehicles per zone.

    Args:
        lookback_days: Days of trip history to analyse (default 7)

    Returns:
        zones: list of {zone, available_vehicles, avg_daily_trips, supply_ratio, status}
        surplus_zones: zones with more vehicles than demand (candidates for rebalancing out)
        deficit_zones: zones with fewer vehicles than demand (need rebalancing in)
        overall_balance: fleet-wide supply/demand ratio
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        now = datetime.now(tz=UTC)
        start_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        vehicles, trips = (
            await _fetch_all_vehicles(runtime_context, config),
            await _fetch_all_trips(runtime_context, config, start_date=start_date, end_date=end_date, status="C"),
        )

        logger.info(f"[zone_demand_supply] vehicles={len(vehicles)} trips={len(trips)}")

        # Count available vehicles per zone
        # Micromobility uses is_available boolean + nested fleet object for zone
        zone_supply: dict[str, int] = {}
        for v in vehicles:
            if v.get("is_available"):
                _fleet = v.get("fleet") or {}
                zone = _fleet.get("name") or _fleet.get("id") or v.get("service_area") or "Unknown"
                zone_supply[zone] = zone_supply.get(zone, 0) + 1

        # Count trips started per zone per day
        # Micromobility trips: zone identified by bike.fleet.address (no name on trips)
        zone_trips: dict[str, list[int]] = {}
        for t in trips:
            _bike = t.get("bike") or {}
            _fleet = _bike.get("fleet") or {}
            zone = _fleet.get("address") or _fleet.get("name") or "Unknown"
            zone_trips.setdefault(zone, [])
            zone_trips[zone].append(1)

        all_zones = set(zone_supply.keys()) | set(zone_trips.keys())
        zone_data = []
        surplus_zones = []
        deficit_zones = []

        for zone in all_zones:
            supply = zone_supply.get(zone, 0)
            trip_count = len(zone_trips.get(zone, []))
            avg_daily = round(trip_count / max(lookback_days, 1), 1)
            ratio = round(supply / avg_daily, 2) if avg_daily > 0 else (99.0 if supply > 0 else 0.0)

            if ratio > 1.5 and supply > _REBALANCE_MIN_SURPLUS:
                status = "surplus"
                surplus_zones.append(zone)
            elif avg_daily > 0 and ratio < 0.6:
                status = "deficit"
                deficit_zones.append(zone)
            else:
                status = "balanced"

            zone_data.append(
                {
                    "service_area": zone,
                    "available_vehicles": supply,
                    "avg_daily_trips": avg_daily,
                    "supply_ratio": ratio,
                    "status": status,
                }
            )

        zone_data.sort(key=lambda z: z["supply_ratio"])

        total_supply = sum(z["available_vehicles"] for z in zone_data)
        total_demand = sum(z["avg_daily_trips"] for z in zone_data)
        overall_balance = round(total_supply / total_demand, 2) if total_demand > 0 else 1.0

        return {
            "success": True,
            "zones": zone_data,
            "surplus_service_areas": surplus_zones,
            "deficit_service_areas": deficit_zones,
            "overall_balance": overall_balance,
            "lookback_days": lookback_days,
            "analysis_timestamp": now.isoformat(),
        }
    except Exception as e:
        logger.error(f"internal_micromobility_get_zone_demand_supply failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_predict_demand(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lat: float = 0.0,
    lng: float = 0.0,
    hours_ahead: int = 24,
    zone: str | None = None,
) -> dict[str, Any]:
    """
    Predict demand for a zone over the next N hours using three signals:
    historical trip patterns (40%), weather conditions (30%), and nearby events (30%).

    Calls weather and events tools automatically if they are configured.

    Args:
        lat: Zone centre latitude (used for weather and event lookups)
        lng: Zone centre longitude
        hours_ahead: Forecast window in hours (1–48)
        zone: Zone name/ID for label in the response

    Returns:
        predicted_demand_index: 0.0–3.0+ composite score (1.0 = baseline)
        confidence: low / medium / high
        signals: breakdown of each signal's contribution
        summary: human-readable forecast
        recommended_vehicle_count: suggested available vehicles for this zone
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        hours_ahead = max(1, min(int(hours_ahead), 48))

        # ── Signal 1: Historical baseline (40% weight) ────────────────────────
        historical_modifier = 1.0
        historical_note = "No trip history available — using baseline"

        try:
            from src.services.agents.internal_tools.micromobility_tools import (
                internal_micromobility_analytics_activity,
            )

            activity_resp = await internal_micromobility_analytics_activity(
                config=config, runtime_context=runtime_context
            )
            logger.info(
                f"[predict_demand] analytics_activity response keys: {list(activity_resp.keys()) if isinstance(activity_resp, dict) else type(activity_resp)}"
            )
            if isinstance(activity_resp, dict) and activity_resp.get("success"):
                # Estimate modifier from hourly activity peaks
                data = activity_resp.get("data") or activity_resp.get("activity") or []
                logger.info(
                    f"[predict_demand] activity data type={type(data)} len={len(data) if isinstance(data, list) else 'n/a'} sample={data[0] if isinstance(data, list) and data else data}"
                )
                if data:
                    values = [float(d.get("value") or d.get("count") or 0) for d in data]
                    if values:
                        avg = sum(values) / len(values)
                        peak = max(values)
                        historical_modifier = round(min(peak / avg, 2.0) if avg > 0 else 1.0, 2)
                        historical_note = f"Peak/avg trip ratio: {historical_modifier:.2f}x"
        except Exception as hist_e:
            logger.debug(f"Historical analysis skipped: {hist_e}")

        # ── Signal 2: Weather modifier (30% weight) ───────────────────────────
        # Try OpenWeather first (requires OAuth app); fall back to Open-Meteo (free, always available).
        weather_modifier = 1.0
        weather_note = "Weather not configured"

        try:
            from src.services.agents.internal_tools.openweather_tools import internal_get_weather_forecast

            weather_resp = await internal_get_weather_forecast(
                config=config, runtime_context=runtime_context, lat=lat, lng=lng, hours_ahead=hours_ahead
            )
            if isinstance(weather_resp, dict) and weather_resp.get("success"):
                weather_modifier = float(weather_resp.get("overall_modifier", 1.0))
                weather_note = weather_resp.get("summary", "")
            else:
                raise ValueError("OpenWeather not configured — trying Open-Meteo")
        except Exception:
            try:
                from src.services.agents.internal_tools.openmeteo_tools import internal_get_openmeteo_forecast

                weather_resp = await internal_get_openmeteo_forecast(
                    config=config, runtime_context=runtime_context, lat=lat, lng=lng, hours_ahead=hours_ahead
                )
                if isinstance(weather_resp, dict) and weather_resp.get("success"):
                    weather_modifier = float(weather_resp.get("overall_modifier", 1.0))
                    weather_note = weather_resp.get("summary", "") + " (via Open-Meteo)"
            except Exception as wx_e:
                logger.debug(f"Weather signal skipped: {wx_e}")

        # ── Signal 3: Events modifier (30% weight) ────────────────────────────
        events_modifier = 1.0
        events_note = "Events not configured"

        try:
            from src.services.agents.internal_tools.events_tools import (
                internal_get_predicthq_events,
                internal_get_ticketmaster_events,
            )

            phq_resp = await internal_get_predicthq_events(
                config=config, runtime_context=runtime_context, lat=lat, lng=lng, hours_ahead=hours_ahead
            )
            tm_resp = await internal_get_ticketmaster_events(
                config=config, runtime_context=runtime_context, lat=lat, lng=lng, hours_ahead=hours_ahead
            )

            phq_mult = float(phq_resp.get("combined_multiplier", 1.0)) if phq_resp.get("success") else 1.0
            tm_mult = float(tm_resp.get("combined_multiplier", 1.0)) if tm_resp.get("success") else 1.0
            events_modifier = max(phq_mult, tm_mult)

            if phq_resp.get("success") or tm_resp.get("success"):
                phq_summary = phq_resp.get("summary", "") if phq_resp.get("success") else ""
                tm_summary = tm_resp.get("summary", "") if tm_resp.get("success") else ""
                events_note = phq_summary or tm_summary or "Events checked"
        except Exception as ev_e:
            logger.debug(f"Events signal skipped: {ev_e}")

        # ── Composite demand index ────────────────────────────────────────────
        composite = (historical_modifier * 0.40) + (weather_modifier * 0.30) + (events_modifier * 0.30)
        composite = round(composite, 2)

        signals_configured = sum(
            [
                historical_modifier != 1.0,
                weather_modifier != 1.0 or weather_note != "Weather not configured",
                events_modifier != 1.0 or events_note != "Events not configured",
            ]
        )
        confidence = "high" if signals_configured >= 2 else ("medium" if signals_configured == 1 else "low")

        if composite >= 1.4:
            summary = (
                f"High demand expected — {round((composite - 1) * 100)}% above baseline. Deploy additional vehicles."
            )
        elif composite <= 0.7:
            summary = (
                f"Low demand expected — {round((1 - composite) * 100)}% below baseline. Consider reducing deployment."
            )
        else:
            summary = (
                f"Moderate demand expected (~{round(composite * 100)}% of baseline). Standard deployment recommended."
            )

        # Rough vehicle count recommendation (operator can calibrate the base)
        base_vehicles = 10
        recommended = max(2, round(base_vehicles * composite))

        return {
            "success": True,
            "service_area": zone or f"({lat:.4f}, {lng:.4f})",
            "hours_ahead": hours_ahead,
            "predicted_demand_index": composite,
            "confidence": confidence,
            "signals": {
                "historical": {"modifier": round(historical_modifier, 2), "weight": 0.40, "note": historical_note},
                "weather": {"modifier": round(weather_modifier, 2), "weight": 0.30, "note": weather_note},
                "events": {"modifier": round(events_modifier, 2), "weight": 0.30, "note": events_note},
            },
            "recommended_vehicle_count": recommended,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"internal_micromobility_predict_demand failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_rebalancing_plan(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lookback_days: int = 7,
    max_moves: int = 10,
) -> dict[str, Any]:
    """
    Generate a rebalancing plan by matching surplus zones to deficit zones.

    Analyses current supply vs demand across all zones and produces a list of
    vehicle moves ordered by impact. Rangers can execute these tasks directly.

    Args:
        lookback_days: Days of trip history used for demand calculation
        max_moves: Maximum number of vehicle moves to include in the plan

    Returns:
        moves: list of {from_zone, to_zone, vehicle_count, priority, reason}
        total_moves: total vehicles to relocate
        estimated_impact: demand improvement score
        ranger_tasks: pre-formatted task descriptions for ranger dispatch
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        demand_resp = await internal_micromobility_get_zone_demand_supply(
            config=config, runtime_context=runtime_context, lookback_days=lookback_days
        )
        if not demand_resp.get("success"):
            return demand_resp

        surplus = sorted(
            [z for z in demand_resp["zones"] if z["status"] == "surplus"],
            key=lambda z: z["supply_ratio"],
            reverse=True,
        )
        deficit = sorted(
            [z for z in demand_resp["zones"] if z["status"] == "deficit"],
            key=lambda z: z["supply_ratio"],
        )

        moves = []
        for def_zone in deficit[:max_moves]:
            if not surplus:
                break
            src = surplus.pop(0)
            vehicles_to_move = min(
                int(src["available_vehicles"] * 0.3) or 1,
                max(1, int(def_zone["avg_daily_trips"] - def_zone["available_vehicles"])),
            )
            vehicles_to_move = max(1, min(vehicles_to_move, 5))

            moves.append(
                {
                    "from_service_area": src["service_area"],
                    "to_service_area": def_zone["service_area"],
                    "vehicle_count": vehicles_to_move,
                    "priority": "high" if def_zone["supply_ratio"] < 0.3 else "medium",
                    "reason": (
                        f"{def_zone['service_area']} has {def_zone['avg_daily_trips']:.0f} avg daily trips "
                        f"but only {def_zone['available_vehicles']} vehicles ({def_zone['supply_ratio']:.1f}x ratio). "
                        f"{src['service_area']} has surplus ({src['supply_ratio']:.1f}x ratio)."
                    ),
                }
            )

        ranger_tasks = [
            (
                f"REBALANCING: Move {m['vehicle_count']} vehicle(s) from {m['from_service_area']} to {m['to_service_area']} "
                f"[{m['priority'].upper()} priority] — {m['reason']}"
            )
            for m in moves
        ]

        total_moves = sum(m["vehicle_count"] for m in moves)
        estimated_impact = round(len(moves) / max(len(deficit), 1), 2) if deficit else 1.0

        return {
            "success": True,
            "moves": moves,
            "total_vehicles_to_move": total_moves,
            "deficit_service_areas": len(deficit),
            "surplus_service_areas": len(surplus) + len(moves),
            "estimated_coverage_improvement": estimated_impact,
            "ranger_tasks": ranger_tasks,
            "lookback_days": lookback_days,
        }
    except Exception as e:
        logger.error(f"internal_micromobility_get_rebalancing_plan failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_batch_create_ranger_tasks(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Create multiple ranger tasks in a single operation.

    Used to dispatch rebalancing, charging, or maintenance tasks in bulk
    after the operator approves a rebalancing plan. Requires confirmation.

    Args:
        tasks: List of task definitions — each with:
            task_type: 'charging' | 'rebalancing' | 'maintenance' | 'inspection'
            vehicle_id: Vehicle to assign (optional)
            notes: Instructions for the ranger
            priority: 'low' | 'medium' | 'high' | 'urgent'

    Returns:
        created: list of {task_id, task_type, vehicle_id, status}
        failed: list of {task_type, vehicle_id, error}
        summary: counts
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    if not tasks:
        return {"success": False, "error": "No tasks provided. Pass a list of task definitions."}

    from src.services.agents.internal_tools.micromobility_tools import internal_micromobility_create_task

    created = []
    failed = []

    for task_def in tasks[:20]:  # cap at 20 tasks per batch
        try:
            resp = await internal_micromobility_create_task(
                config=config,
                runtime_context=runtime_context,
                task_type=task_def.get("task_type", "rebalancing"),
                vehicle_id=task_def.get("vehicle_id"),
                operator_id=task_def.get("operator_id"),
                notes=task_def.get("notes"),
                priority=task_def.get("priority", "medium"),
            )
            if isinstance(resp, dict) and resp.get("success"):
                task_data = resp.get("task") or resp.get("data") or resp
                created.append(
                    {
                        "task_id": task_data.get("id") or task_data.get("task_id"),
                        "task_type": task_def.get("task_type"),
                        "vehicle_id": task_def.get("vehicle_id"),
                        "status": "created",
                    }
                )
            else:
                failed.append(
                    {
                        "task_type": task_def.get("task_type"),
                        "vehicle_id": task_def.get("vehicle_id"),
                        "error": str(resp.get("error") if isinstance(resp, dict) else resp),
                    }
                )
        except Exception as e:
            failed.append(
                {
                    "task_type": task_def.get("task_type"),
                    "vehicle_id": task_def.get("vehicle_id"),
                    "error": str(e),
                }
            )

    return {
        "success": True,
        "created": created,
        "failed": failed,
        "summary": {
            "total_requested": len(tasks),
            "created": len(created),
            "failed": len(failed),
        },
    }


async def internal_micromobility_get_trip_performance(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """
    Compute trip performance KPIs for the last N days.

    Aggregates completed trips to produce: total trips, avg duration,
    avg distance, completion rate, cancellation rate, revenue estimate,
    peak hour, and top performing zones.

    Args:
        days: Lookback period in days (default 30)

    Returns:
        kpis: dict of key performance indicators
        peak_hour: hour of day with most trips (0-23)
        top_zones: list of zones by trip count
        trend: daily trip count over the period
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        now = datetime.now(tz=UTC)
        start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        # Micromobility status codes: "C" = completed. Cancelled code unknown — fetch all and filter by status field.
        completed = await _fetch_all_trips(runtime_context, config, start_date=start, end_date=end, status="C")
        cancelled = await _fetch_all_trips(runtime_context, config, start_date=start, end_date=end, status="cancelled")

        logger.info(
            f"[trip_performance] fetched completed={len(completed)} cancelled={len(cancelled)} for period {start} → {end}"
        )

        total_completed = len(completed)
        total_cancelled = len(cancelled)
        total = total_completed + total_cancelled

        # riding_time is in seconds; convert to minutes
        durations = [float(t.get("riding_time") or 0) / 60 for t in completed]
        # distance is a string (e.g. "0" or "1.23")
        distances = [float(t.get("distance") or 0) for t in completed]
        # revenue is in invoiced_charges.amount (string)
        revenues = [float((t.get("invoiced_charges") or {}).get("amount") or 0) for t in completed]

        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
        avg_distance = round(sum(distances) / len(distances), 2) if distances else 0
        total_revenue = round(sum(revenues), 2)

        # Hourly distribution — Micromobility uses pick_up_time
        hour_counts: dict[int, int] = {}
        for t in completed:
            start_ts = t.get("pick_up_time") or ""
            h = _hours_since(start_ts)
            if h is not None:
                hour_of_day = (now - timedelta(hours=h)).hour
                hour_counts[hour_of_day] = hour_counts.get(hour_of_day, 0) + 1

        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None

        # Zone breakdown — Micromobility trips: zone is bike.fleet.address (no fleet name on trips)
        zone_counts: dict[str, int] = {}
        for t in completed:
            _bike = t.get("bike") or {}
            _fleet = _bike.get("fleet") or {}
            zone = _fleet.get("address") or _fleet.get("name") or "Unknown"
            zone_counts[zone] = zone_counts.get(zone, 0) + 1

        top_zones = sorted(
            [{"service_area": z, "trip_count": c} for z, c in zone_counts.items()],
            key=lambda x: x["trip_count"],
            reverse=True,
        )[:10]

        return {
            "success": True,
            "period_days": days,
            "kpis": {
                "total_trips": total,
                "completed_trips": total_completed,
                "cancelled_trips": total_cancelled,
                "completion_rate_pct": round(total_completed / total * 100, 1) if total else 0,
                "cancellation_rate_pct": round(total_cancelled / total * 100, 1) if total else 0,
                "avg_duration_minutes": avg_duration,
                "avg_distance_km": avg_distance,
                "total_revenue": total_revenue,
                "avg_revenue_per_trip": round(total_revenue / total_completed, 2) if total_completed else 0,
                "trips_per_day": round(total_completed / days, 1),
            },
            "peak_hour": peak_hour,
            "top_zones": top_zones,
        }
    except Exception as e:
        logger.error(f"internal_micromobility_get_trip_performance failed: {e}")
        return {"success": False, "error": str(e)}
