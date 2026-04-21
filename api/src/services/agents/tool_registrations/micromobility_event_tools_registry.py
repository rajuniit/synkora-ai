"""Micromobility Event Impact & IoT Intelligence Tools Registry."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_micromobility_event_tools(registry) -> None:
    from src.services.agents.internal_tools.micromobility_event_tools import (
        internal_micromobility_analyze_event_impact,
        internal_micromobility_get_battery_degradation,
        internal_micromobility_get_network_health,
        internal_micromobility_get_parking_compliance,
        internal_micromobility_get_ranger_performance,
    )

    async def _event_impact_wrapper(config: dict[str, Any] | None = None, **kwargs):
        rc = config.get("_runtime_context") if config else None
        return await internal_micromobility_analyze_event_impact(
            config=config, runtime_context=rc,
            event_date=kwargs.get("event_date", ""),
            event_start_hour=int(kwargs.get("event_start_hour", 0)),
            event_end_hour=int(kwargs.get("event_end_hour", 23)),
            description=kwargs.get("description", ""),
            baseline_weeks=int(kwargs.get("baseline_weeks", 4)),
            zone=kwargs.get("service_area"),
        )

    async def _network_health_wrapper(config: dict[str, Any] | None = None, **kwargs):
        rc = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_network_health(
            config=config, runtime_context=rc,
            offline_threshold_hours=int(kwargs.get("offline_threshold_hours", 2)),
        )

    async def _parking_compliance_wrapper(config: dict[str, Any] | None = None, **kwargs):
        rc = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_parking_compliance(
            config=config, runtime_context=rc,
            lookback_days=int(kwargs.get("lookback_days", 7)),
        )

    async def _battery_degradation_wrapper(config: dict[str, Any] | None = None, **kwargs):
        rc = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_battery_degradation(
            config=config, runtime_context=rc,
            min_trips=int(kwargs.get("min_trips", 10)),
            degradation_threshold_pct_per_trip=float(kwargs.get("degradation_threshold_pct_per_trip", 2.0)),
        )

    async def _ranger_perf_wrapper(config: dict[str, Any] | None = None, **kwargs):
        rc = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_ranger_performance(
            config=config, runtime_context=rc,
            days=int(kwargs.get("days", 14)),
        )

    registry.register_tool(
        name="internal_micromobility_analyze_event_impact",
        description=(
            "Measure how an external event (transit strike, concert, sports match, public holiday, weather incident) "
            "affected OtoRide trip demand by comparing trip volumes during the event window against "
            "the same weekday+hour window from prior weeks. "
            "Use this when the operator asks how a specific event or disruption affected demand or bookings."
        ),
        parameters={
            "type": "object",
            "properties": {
                "event_date": {"type": "string", "description": "Date of the event in YYYY-MM-DD format"},
                "event_start_hour": {"type": "integer", "description": "Start of event window (0-23, e.g. 8 for 8 AM)"},
                "event_end_hour": {"type": "integer", "description": "End of event window (0-23, e.g. 11 for 11 AM)"},
                "description": {"type": "string", "description": "Human label for the event (e.g. 'Metro Line 8 strike', 'Taylor Swift concert')"},
                "baseline_weeks": {"type": "integer", "description": "Prior same-weekday windows to use as baseline (default 4)"},
                "service_area": {"type": "string", "description": "Optional — restrict to a specific service area name"},
            },
            "required": ["event_date"],
        },
        function=_event_impact_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_network_health",
        description=(
            "Identify IoT connectivity issues: vehicles that are offline or silent beyond a threshold. "
            "Groups offline vehicles by service area to surface connectivity dead spots — "
            "areas where vehicles consistently lose IoT signal. "
            "Use when the operator asks about unreachable vehicles, offline devices, or connectivity problems."
        ),
        parameters={
            "type": "object",
            "properties": {
                "offline_threshold_hours": {
                    "type": "integer",
                    "description": "Hours without heartbeat before flagging a vehicle (default 2)",
                },
            },
            "required": [],
        },
        function=_network_health_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_parking_compliance",
        description=(
            "Analyse how many trips ended outside designated parking areas. "
            "Identifies non-compliant parking by service area and estimates the ranger hours needed to relocate misparked vehicles. "
            "Use when the operator asks about parking violations, city compliance, or ranger relocation workload."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lookback_days": {"type": "integer", "description": "Days of trip history to analyse (default 7)"},
            },
            "required": [],
        },
        function=_parking_compliance_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_battery_degradation",
        description=(
            "Identify vehicles with abnormal battery drain patterns using trip-level battery data. "
            "Flags vehicles whose average drain per trip exceeds the threshold — likely candidates for "
            "battery replacement before they fail in the field. "
            "Use for predictive maintenance planning."
        ),
        parameters={
            "type": "object",
            "properties": {
                "min_trips": {"type": "integer", "description": "Minimum trips needed to compute drain rate (default 10)"},
                "degradation_threshold_pct_per_trip": {
                    "type": "number",
                    "description": "Flag vehicles draining more than this % per trip (default 2.0)",
                },
            },
            "required": [],
        },
        function=_battery_degradation_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_ranger_performance",
        description=(
            "Analyse ranger (field operations) performance: task completion rates, average task duration, "
            "and workload distribution. Identifies rangers with low completion rates or high delays. "
            "Use when the operator asks about team performance, shift efficiency, or task backlogs."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Lookback period in days (default 14)"},
            },
            "required": [],
        },
        function=_ranger_perf_wrapper,
    )

    logger.info("Registered 5 Micromobility Event & IoT Intelligence tools")
