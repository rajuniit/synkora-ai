"""
Micromobility Event Impact & IoT Intelligence Tools.

Tools that cross-reference OtoRide trip/vehicle data with external events,
IoT telemetry patterns, and geofence compliance — giving operators insights
that go beyond standard fleet dashboards.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _fetch_trips_window(
    runtime_context: Any,
    config: Any,
    date_str: str,
    start_hour: int,
    end_hour: int,
    status: str = "completed",
) -> list[dict[str, Any]]:
    """Fetch trips for a specific date within a time window (hours)."""
    from src.services.agents.internal_tools.micromobility_tools import internal_micromobility_list_trips

    all_trips: list[dict[str, Any]] = []
    offset = 0
    while True:
        resp = await internal_micromobility_list_trips(
            config=config,
            runtime_context=runtime_context,
            start_date=date_str,
            end_date=date_str,
            status=status,
            limit=100,
            offset=offset,
        )
        if not isinstance(resp, dict) or not resp.get("success"):
            break
        raw = resp.get("data")
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("trips") or raw.get("results") or raw.get("data") or []
        else:
            items = resp.get("trips") or resp.get("results") or []
        if not items:
            break

        # Filter to the hour window
        for t in items:
            ts_str = t.get("started_at") or t.get("created_at") or ""
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if start_hour <= ts.hour < end_hour:
                        all_trips.append(t)
                except Exception:
                    pass
            else:
                all_trips.append(t)  # include if no timestamp

        if len(items) < 100:
            break
        offset += 100
        if offset > 1000:
            break
    return all_trips


def _zone_breakdown(trips: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in trips:
        zone = t.get("service_area") or t.get("start_zone") or t.get("fleet_id") or "Unknown"
        counts[zone] = counts.get(zone, 0) + 1
    return counts


def _weekday_name(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    except Exception:
        return date_str


# ── Event Impact Analysis ─────────────────────────────────────────────────────


async def internal_micromobility_analyze_event_impact(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    event_date: str = "",
    event_start_hour: int = 0,
    event_end_hour: int = 23,
    description: str = "",
    baseline_weeks: int = 4,
    zone: str | None = None,
) -> dict[str, Any]:
    """
    Measure how an external event (strike, concert, weather incident, public holiday)
    affected OtoRide demand by comparing trip volumes during the event window against
    the same weekday+hour window from prior weeks.

    The LLM describes the external event (from training knowledge or news tools);
    this tool provides the OtoRide demand response — demand delta, hotspot zones,
    and one-way vs round-trip ratio if available.

    Args:
        event_date: Date of the event in YYYY-MM-DD format
        event_start_hour: Start of the event window (0-23, e.g. 8 for 8 AM)
        event_end_hour: End of the event window (0-23, e.g. 11 for 11 AM)
        description: Human label for the event (e.g. 'Metro Line 8 strike')
        baseline_weeks: Number of prior same-weekday windows to use as baseline (default 4)
        zone: Optional — restrict analysis to a specific service area name

    Returns:
        event_trips: trip count during the event window
        baseline_avg: average trip count for the same window in prior weeks
        demand_delta_pct: percentage change vs baseline (positive = increase)
        hotspot_zones: zones with the highest demand increase, sorted descending
        one_way_ratio: fraction of trips that were one-way (if data available)
        summary: human-readable impact description
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    if not event_date:
        return {"success": False, "error": "event_date is required (YYYY-MM-DD)."}

    try:
        event_start_hour = max(0, min(int(event_start_hour), 23))
        event_end_hour = max(event_start_hour + 1, min(int(event_end_hour), 24))
        baseline_weeks = max(1, min(int(baseline_weeks), 8))

        # ── Event window trips ────────────────────────────────────────────────
        event_trips = await _fetch_trips_window(runtime_context, config, event_date, event_start_hour, event_end_hour)

        # Optional zone filter
        if zone:
            event_trips = [t for t in event_trips if zone.lower() in (t.get("service_area") or "").lower()]

        event_count = len(event_trips)
        event_zone_counts = _zone_breakdown(event_trips)

        # ── Baseline: same weekday from prior N weeks ─────────────────────────
        event_dt = datetime.strptime(event_date, "%Y-%m-%d")
        baseline_counts: list[int] = []
        baseline_zone_counts: dict[str, list[int]] = {}

        for w in range(1, baseline_weeks + 1):
            baseline_dt = event_dt - timedelta(weeks=w)
            baseline_date = baseline_dt.strftime("%Y-%m-%d")
            base_trips = await _fetch_trips_window(
                runtime_context, config, baseline_date, event_start_hour, event_end_hour
            )
            if zone:
                base_trips = [t for t in base_trips if zone.lower() in (t.get("service_area") or "").lower()]
            baseline_counts.append(len(base_trips))
            bz = _zone_breakdown(base_trips)
            for z, c in bz.items():
                baseline_zone_counts.setdefault(z, []).append(c)

        baseline_avg = round(sum(baseline_counts) / len(baseline_counts), 1) if baseline_counts else 0

        # ── Delta ─────────────────────────────────────────────────────────────
        if baseline_avg > 0:
            demand_delta_pct = round((event_count - baseline_avg) / baseline_avg * 100, 1)
        elif event_count > 0:
            demand_delta_pct = 100.0
        else:
            demand_delta_pct = 0.0

        # ── Hotspot zones (sorted by delta vs baseline) ───────────────────────
        hotspot_zones = []
        all_zones = set(event_zone_counts.keys()) | set(baseline_zone_counts.keys())
        for z in all_zones:
            ev = event_zone_counts.get(z, 0)
            base_list = baseline_zone_counts.get(z, [0])
            base_mean = sum(base_list) / len(base_list)
            delta = round((ev - base_mean) / base_mean * 100, 1) if base_mean > 0 else (100.0 if ev > 0 else 0.0)
            hotspot_zones.append(
                {
                    "service_area": z,
                    "event_trips": ev,
                    "baseline_avg": round(base_mean, 1),
                    "delta_pct": delta,
                }
            )
        hotspot_zones.sort(key=lambda x: x["delta_pct"], reverse=True)

        # ── One-way ratio (if trip_type or distance available) ────────────────
        one_way_count = sum(
            1
            for t in event_trips
            if (t.get("trip_type") or "").lower() in ("one_way", "one-way") or (t.get("is_round_trip") is False)
        )
        one_way_ratio = round(one_way_count / event_count, 2) if event_count > 0 else None

        # ── Summary ───────────────────────────────────────────────────────────
        weekday = _weekday_name(event_date)
        label = description or f"event on {event_date}"
        window_str = f"{event_start_hour:02d}:00–{event_end_hour:02d}:00"
        direction = "increase" if demand_delta_pct >= 0 else "decrease"
        top_zone = hotspot_zones[0]["service_area"] if hotspot_zones else "N/A"

        if abs(demand_delta_pct) < 5:
            summary = f"The {label} had minimal impact on OtoRide demand during {window_str} (±{abs(demand_delta_pct)}% vs {weekday} baseline)."
        else:
            summary = (
                f"The {label} drove a {abs(demand_delta_pct):.0f}% demand {direction} "
                f"during {window_str} vs the {baseline_weeks}-week {weekday} baseline. "
                f"Hotspot service area: {top_zone} ({hotspot_zones[0]['delta_pct']:+.0f}%)."
            )
            if one_way_ratio and one_way_ratio > 0.6:
                summary += f" {round(one_way_ratio * 100)}% of trips were one-way, indicating directional demand."

        return {
            "success": True,
            "event_date": event_date,
            "event_window": f"{event_start_hour:02d}:00–{event_end_hour:02d}:00",
            "description": label,
            "event_trips": event_count,
            "baseline_avg_trips": baseline_avg,
            "baseline_weeks_used": baseline_weeks,
            "demand_delta_pct": demand_delta_pct,
            "hotspot_service_areas": hotspot_zones[:8],
            "one_way_ratio": one_way_ratio,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_micromobility_analyze_event_impact failed: {e}")
        return {"success": False, "error": str(e)}


# ── Network / IoT Health ──────────────────────────────────────────────────────


async def internal_micromobility_get_network_health(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    offline_threshold_hours: int = 2,
) -> dict[str, Any]:
    """
    Identify IoT connectivity issues across the fleet by finding vehicles
    that are in 'offline' status or haven't reported a location recently.

    Groups offline vehicles by service area to surface connectivity dead zones —
    areas where vehicles consistently lose IoT signal.

    Args:
        offline_threshold_hours: Hours without heartbeat before flagging (default 2)

    Returns:
        offline_vehicles: list of offline vehicles with zone and last-seen time
        dead_zones: service areas with disproportionately high offline rates
        connectivity_rate_pct: fleet-wide IoT connectivity percentage
        summary: human-readable diagnosis
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        from src.services.agents.internal_tools.micromobility_intelligence_tools import (
            _fetch_all_vehicles,
            _hours_since,
        )

        vehicles = await _fetch_all_vehicles(runtime_context, config)
        if not vehicles:
            return {"success": False, "error": "No vehicle data returned from OtoRide API."}

        total = len(vehicles)
        offline_vehicles = []
        zone_total: dict[str, int] = {}
        zone_offline: dict[str, int] = {}

        for v in vehicles:
            vid = v.get("id") or v.get("vehicle_id", "")
            status = (v.get("status") or "").lower()
            zone = v.get("service_area") or v.get("zone") or v.get("fleet_id") or "Unknown"
            zone_total[zone] = zone_total.get(zone, 0) + 1

            last_seen = v.get("last_heartbeat_at") or v.get("last_location_at") or v.get("updated_at")
            hours_silent = _hours_since(last_seen)

            is_offline = status == "offline" or (hours_silent is not None and hours_silent >= offline_threshold_hours)

            if is_offline:
                zone_offline[zone] = zone_offline.get(zone, 0) + 1
                offline_vehicles.append(
                    {
                        "vehicle_id": vid,
                        "service_area": zone,
                        "status": status,
                        "hours_silent": round(hours_silent, 1) if hours_silent else None,
                        "last_seen": last_seen,
                    }
                )

        # Dead spots: offline rate > 30% with at least 3 vehicles
        dead_zones = []
        for zone, total_z in zone_total.items():
            offline_z = zone_offline.get(zone, 0)
            rate = offline_z / total_z if total_z > 0 else 0
            if rate > 0.30 and total_z >= 3:
                dead_zones.append(
                    {
                        "service_area": zone,
                        "offline_vehicles": offline_z,
                        "total_vehicles": total_z,
                        "offline_rate_pct": round(rate * 100, 1),
                    }
                )
        dead_zones.sort(key=lambda z: z["offline_rate_pct"], reverse=True)

        total_offline = len(offline_vehicles)
        connectivity_rate = round((total - total_offline) / total * 100, 1) if total else 100.0

        if total_offline == 0:
            summary = f"All {total} vehicles are online. Fleet connectivity is at 100%."
        else:
            summary = (
                f"{total_offline} of {total} vehicles are offline or silent (connectivity rate: {connectivity_rate}%). "
            )
            if dead_zones:
                summary += f"Connectivity dead spot: {dead_zones[0]['service_area']} has {dead_zones[0]['offline_rate_pct']}% offline rate."

        offline_vehicles.sort(key=lambda x: x.get("hours_silent") or 0, reverse=True)

        return {
            "success": True,
            "total_vehicles": total,
            "offline_count": total_offline,
            "connectivity_rate_pct": connectivity_rate,
            "offline_threshold_hours": offline_threshold_hours,
            "offline_vehicles": offline_vehicles[:20],
            "offline_service_areas": dead_zones,
            "recommended_actions": [
                f"Dispatch ranger to {dead_zones[0]['service_area']} — {dead_zones[0]['offline_rate_pct']}% of vehicles offline"
            ]
            if dead_zones
            else ["Fleet connectivity is healthy — no action required"],
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_micromobility_get_network_health failed: {e}")
        return {"success": False, "error": str(e)}


# ── Parking Compliance ────────────────────────────────────────────────────────


async def internal_micromobility_get_parking_compliance(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """
    Analyse how many trips ended outside designated parking areas (non-compliant parking).

    Non-compliant parking degrades city relationships, triggers fines, and forces
    rangers to relocate vehicles. This tool identifies the worst offending zones
    and estimates the operational cost.

    Args:
        lookback_days: Days of trip history to analyse (default 7)

    Returns:
        non_compliant_trips: count of trips ending outside parking areas
        compliance_rate_pct: percentage of trips ending in a valid parking area
        worst_zones: zones with highest non-compliance rates
        estimated_relocation_cost: rough ranger-hours needed to fix misparked vehicles
        summary: human-readable compliance summary
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        from datetime import UTC, datetime, timedelta

        from src.services.agents.internal_tools.micromobility_intelligence_tools import _fetch_all_trips

        now = datetime.now(tz=UTC)
        start = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        trips = await _fetch_all_trips(runtime_context, config, start_date=start, end_date=end, status="completed")
        total = len(trips)
        if total == 0:
            return {
                "success": True,
                "compliance_rate_pct": 100.0,
                "non_compliant_trips": 0,
                "summary": "No completed trips in the period.",
            }

        # Check parking_area field on trip — OtoRide sets this when trip ends in a valid area
        non_compliant = [
            t for t in trips if not (t.get("parking_area") or t.get("end_parking_area") or t.get("parked_in_area"))
        ]
        non_compliant_count = len(non_compliant)
        compliance_rate = round((total - non_compliant_count) / total * 100, 1)

        # Zone breakdown of non-compliant trips
        zone_counts: dict[str, int] = {}
        zone_total: dict[str, int] = {}
        for t in trips:
            zone = t.get("service_area") or t.get("end_zone") or "Unknown"
            zone_total[zone] = zone_total.get(zone, 0) + 1
        for t in non_compliant:
            zone = t.get("service_area") or t.get("end_zone") or "Unknown"
            zone_counts[zone] = zone_counts.get(zone, 0) + 1

        worst_zones = sorted(
            [
                {
                    "service_area": z,
                    "non_compliant": c,
                    "total": zone_total.get(z, c),
                    "non_compliance_rate_pct": round(c / zone_total.get(z, c) * 100, 1),
                }
                for z, c in zone_counts.items()
            ],
            key=lambda x: x["non_compliance_rate_pct"],
            reverse=True,
        )[:8]

        # Estimate: 20 min ranger time per relocation
        estimated_ranger_hours = round(non_compliant_count * 20 / 60, 1)

        summary = (
            f"{non_compliant_count} of {total} trips ({100 - compliance_rate:.0f}%) ended outside "
            f"designated parking areas over the last {lookback_days} days. "
        )
        if worst_zones:
            w = worst_zones[0]
            summary += f"Worst service area: {w['service_area']} ({w['non_compliance_rate_pct']}% non-compliant). "
        summary += f"Estimated ranger relocation time: ~{estimated_ranger_hours}h."

        return {
            "success": True,
            "period_days": lookback_days,
            "total_trips": total,
            "non_compliant_trips": non_compliant_count,
            "compliance_rate_pct": compliance_rate,
            "worst_service_areas": worst_zones,
            "estimated_relocation_ranger_hours": estimated_ranger_hours,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_micromobility_get_parking_compliance failed: {e}")
        return {"success": False, "error": str(e)}


# ── Battery Degradation / Predictive Maintenance ──────────────────────────────


async def internal_micromobility_get_battery_degradation(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    min_trips: int = 10,
    degradation_threshold_pct_per_trip: float = 2.0,
) -> dict[str, Any]:
    """
    Identify vehicles with abnormal battery drain patterns that may need
    battery replacement or servicing — predictive maintenance before failure.

    Compares battery level at trip start vs trip end across recent trips.
    Vehicles draining more than the threshold per trip are flagged.

    Args:
        min_trips: Minimum trips required to compute drain rate (default 10)
        degradation_threshold_pct_per_trip: Flag if avg drain exceeds this % per trip (default 2.0)

    Returns:
        flagged_vehicles: vehicles with above-threshold drain rates
        fleet_avg_drain_pct: fleet-wide average drain per trip
        summary: human-readable maintenance recommendation
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        from src.services.agents.internal_tools.micromobility_intelligence_tools import _fetch_all_trips

        now = datetime.now(tz=UTC)
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        trips = await _fetch_all_trips(runtime_context, config, start_date=start, end_date=end, status="completed")

        vehicle_drains: dict[str, list[float]] = {}
        for t in trips:
            vid = t.get("vehicle_id") or t.get("vehicle")
            if not vid:
                continue
            start_bat = t.get("battery_level_start") or t.get("start_battery")
            end_bat = t.get("battery_level_end") or t.get("end_battery")
            if start_bat is not None and end_bat is not None:
                try:
                    drain = float(start_bat) - float(end_bat)
                    if drain >= 0:  # ignore negative drain (charging mid-trip edge cases)
                        vehicle_drains.setdefault(vid, []).append(drain)
                except (ValueError, TypeError):
                    pass

        all_drains = [d for drains in vehicle_drains.values() for d in drains]
        fleet_avg = round(sum(all_drains) / len(all_drains), 2) if all_drains else 0.0

        flagged = []
        for vid, drains in vehicle_drains.items():
            if len(drains) < min_trips:
                continue
            avg_drain = sum(drains) / len(drains)
            if avg_drain > degradation_threshold_pct_per_trip:
                flagged.append(
                    {
                        "vehicle_id": vid,
                        "avg_drain_pct_per_trip": round(avg_drain, 2),
                        "trips_analysed": len(drains),
                        "vs_fleet_avg": round(avg_drain - fleet_avg, 2),
                        "urgency": "high" if avg_drain > degradation_threshold_pct_per_trip * 2 else "medium",
                    }
                )

        flagged.sort(key=lambda x: x["avg_drain_pct_per_trip"], reverse=True)

        summary = (
            f"Fleet average battery drain: {fleet_avg}% per trip. "
            f"{len(flagged)} vehicle(s) exceed the {degradation_threshold_pct_per_trip}% threshold — "
            "likely candidates for battery inspection or replacement."
            if flagged
            else f"Fleet battery health is normal. Average drain: {fleet_avg}% per trip."
        )

        return {
            "success": True,
            "fleet_avg_drain_pct_per_trip": fleet_avg,
            "degradation_threshold": degradation_threshold_pct_per_trip,
            "flagged_vehicles": flagged[:20],
            "total_flagged": len(flagged),
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_micromobility_get_battery_degradation failed: {e}")
        return {"success": False, "error": str(e)}


# ── Ranger Performance Analytics ─────────────────────────────────────────────


async def internal_micromobility_get_ranger_performance(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    days: int = 14,
) -> dict[str, Any]:
    """
    Analyse ranger (field operations) performance: task completion rates,
    average task duration, and workload distribution across rangers.

    Identifies rangers with low completion rates or high delays so team leads
    can provide coaching or redistribute workload.

    Args:
        days: Lookback period in days (default 14)

    Returns:
        rangers: list of {ranger_id, completed, pending, avg_duration_min, completion_rate_pct}
        fleet_avg_completion_rate: fleet-wide average
        slowest_task_type: task type with highest avg completion time
        summary: human-readable performance overview
    """
    if not runtime_context:
        return {"success": False, "error": "No runtime context available."}
    try:
        from src.services.agents.internal_tools.micromobility_intelligence_tools import _hours_since
        from src.services.agents.internal_tools.micromobility_tools import internal_micromobility_list_tasks

        now = datetime.now(tz=UTC)
        start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        all_tasks: list[dict[str, Any]] = []
        offset = 0
        while True:
            resp = await internal_micromobility_list_tasks(
                config=config, runtime_context=runtime_context, start_date=start, end_date=end, limit=100, offset=offset
            )
            if not isinstance(resp, dict) or not resp.get("success"):
                break
            raw = resp.get("data")
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict):
                items = raw.get("tasks") or raw.get("results") or raw.get("data") or []
            else:
                items = resp.get("tasks") or resp.get("results") or []
            if not items:
                break
            all_tasks.extend(items)
            if len(items) < 100:
                break
            offset += 100
            if offset > 2000:
                break

        if not all_tasks:
            return {"success": True, "rangers": [], "summary": "No task data available for this period."}

        ranger_stats: dict[str, dict[str, Any]] = {}
        task_type_durations: dict[str, list[float]] = {}

        for t in all_tasks:
            ranger_id = t.get("assigned_to") or t.get("ranger_id") or t.get("operator_id") or "Unassigned"
            task_type = t.get("task_type") or t.get("type") or "unknown"
            status = (t.get("status") or "").lower()
            created = t.get("created_at") or ""
            completed_at = t.get("completed_at") or ""

            if ranger_id not in ranger_stats:
                ranger_stats[ranger_id] = {"completed": 0, "pending": 0, "cancelled": 0, "durations": []}

            if status in ("completed", "done"):
                ranger_stats[ranger_id]["completed"] += 1
                if created and completed_at:
                    h_created = _hours_since(created)
                    h_completed = _hours_since(completed_at)
                    if h_created is not None and h_completed is not None:
                        duration_min = round((h_created - h_completed) * 60, 1)
                        if duration_min > 0:
                            ranger_stats[ranger_id]["durations"].append(duration_min)
                            task_type_durations.setdefault(task_type, []).append(duration_min)
            elif status in ("pending", "assigned", "in_progress"):
                ranger_stats[ranger_id]["pending"] += 1
            elif status in ("cancelled", "failed"):
                ranger_stats[ranger_id]["cancelled"] += 1

        rangers = []
        for rid, s in ranger_stats.items():
            total_r = s["completed"] + s["pending"] + s["cancelled"]
            completion_rate = round(s["completed"] / total_r * 100, 1) if total_r > 0 else 0.0
            avg_duration = round(sum(s["durations"]) / len(s["durations"]), 1) if s["durations"] else None
            rangers.append(
                {
                    "ranger_id": rid,
                    "completed_tasks": s["completed"],
                    "pending_tasks": s["pending"],
                    "completion_rate_pct": completion_rate,
                    "avg_task_duration_min": avg_duration,
                }
            )

        rangers.sort(key=lambda r: r["completion_rate_pct"])

        fleet_rates = [r["completion_rate_pct"] for r in rangers]
        fleet_avg = round(sum(fleet_rates) / len(fleet_rates), 1) if fleet_rates else 0.0

        slowest_type = (
            max(task_type_durations, key=lambda k: sum(task_type_durations[k]) / len(task_type_durations[k]))
            if task_type_durations
            else None
        )
        slowest_avg = (
            round(sum(task_type_durations[slowest_type]) / len(task_type_durations[slowest_type]), 1)
            if slowest_type
            else None
        )

        low_performers = [r for r in rangers if r["completion_rate_pct"] < 70 and r["ranger_id"] != "Unassigned"]
        summary = (
            f"Fleet-wide task completion rate: {fleet_avg}% over the last {days} days. "
            f"{len(low_performers)} ranger(s) below 70% completion rate. "
        )
        if slowest_type:
            summary += f"Slowest task type: {slowest_type} (avg {slowest_avg} min)."

        return {
            "success": True,
            "period_days": days,
            "fleet_avg_completion_rate_pct": fleet_avg,
            "rangers": rangers,
            "slowest_task_type": slowest_type,
            "slowest_task_avg_min": slowest_avg,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"internal_micromobility_get_ranger_performance failed: {e}")
        return {"success": False, "error": str(e)}
