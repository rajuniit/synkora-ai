"""Micromobility Intelligence Tools Registry — computed fleet analytics."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_micromobility_intelligence_tools(registry) -> None:
    from src.services.agents.internal_tools.micromobility_intelligence_tools import (
        internal_micromobility_batch_create_ranger_tasks,
        internal_micromobility_get_fleet_health,
        internal_micromobility_get_rebalancing_plan,
        internal_micromobility_get_trip_performance,
        internal_micromobility_get_zone_demand_supply,
        internal_micromobility_predict_demand,
    )

    async def _fleet_health_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_fleet_health(
            config=config,
            runtime_context=runtime_context,
            low_battery_threshold=int(kwargs.get("low_battery_threshold", 20)),
            idle_hours_threshold=int(kwargs.get("idle_hours_threshold", 4)),
        )

    async def _zone_demand_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_zone_demand_supply(
            config=config,
            runtime_context=runtime_context,
            lookback_days=int(kwargs.get("lookback_days", 7)),
        )

    async def _predict_demand_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_predict_demand(
            config=config,
            runtime_context=runtime_context,
            lat=float(kwargs.get("lat", 0.0)),
            lng=float(kwargs.get("lng", 0.0)),
            hours_ahead=int(kwargs.get("hours_ahead", 24)),
            zone=kwargs.get("service_area"),
        )

    async def _rebalancing_plan_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_rebalancing_plan(
            config=config,
            runtime_context=runtime_context,
            lookback_days=int(kwargs.get("lookback_days", 7)),
            max_moves=int(kwargs.get("max_moves", 10)),
        )

    async def _batch_tasks_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_batch_create_ranger_tasks(
            config=config,
            runtime_context=runtime_context,
            tasks=kwargs.get("tasks", []),
        )

    async def _trip_performance_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_trip_performance(
            config=config,
            runtime_context=runtime_context,
            days=int(kwargs.get("days", 30)),
        )

    registry.register_tool(
        name="internal_micromobility_get_fleet_health",
        description=(
            "Analyse the health of the entire vehicle fleet: battery levels, idle vehicles, and maintenance status. "
            "Returns pre-computed KPIs and a prioritised list of recommended actions. "
            "Use this instead of listing all vehicles manually — it handles pagination and analysis automatically."
        ),
        parameters={
            "type": "object",
            "properties": {
                "low_battery_threshold": {
                    "type": "integer",
                    "description": "Battery % below which a vehicle is flagged as low-battery (default 20)",
                },
                "idle_hours_threshold": {
                    "type": "integer",
                    "description": "Hours since last trip before a vehicle is considered idle (default 4)",
                },
            },
            "required": [],
        },
        function=_fleet_health_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_zone_demand_supply",
        description=(
            "Compare current vehicle supply vs historical trip demand across all service areas. "
            "Identifies surplus service areas (too many vehicles) and deficit service areas (not enough vehicles). "
            "Use as the first step before generating a rebalancing plan."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lookback_days": {
                    "type": "integer",
                    "description": "Days of trip history to use for demand calculation (default 7)",
                },
            },
            "required": [],
        },
        function=_zone_demand_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_predict_demand",
        description=(
            "Predict demand for a location over the next N hours using three signals: "
            "historical trip patterns (40%), weather conditions (30%), and nearby events (30%). "
            "Returns a demand index (1.0 = baseline), confidence level, and recommended vehicle count. "
            "Automatically calls weather and event tools if they are configured."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Service area centre latitude"},
                "lng": {"type": "number", "description": "Service area centre longitude"},
                "hours_ahead": {
                    "type": "integer",
                    "description": "Forecast window in hours (1–48, default 24)",
                },
                "service_area": {
                    "type": "string",
                    "description": "Service area name or ID for labelling (optional)",
                },
            },
            "required": ["lat", "lng"],
        },
        function=_predict_demand_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_rebalancing_plan",
        description=(
            "Generate a vehicle rebalancing plan by matching surplus service areas to deficit service areas. "
            "Returns an ordered list of vehicle moves with priorities and ranger task descriptions. "
            "Show this to the operator and ask for confirmation before creating actual tasks."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lookback_days": {
                    "type": "integer",
                    "description": "Days of trip history used for demand calculation (default 7)",
                },
                "max_moves": {
                    "type": "integer",
                    "description": "Maximum number of vehicle moves to include (default 10)",
                },
            },
            "required": [],
        },
        function=_rebalancing_plan_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_batch_create_ranger_tasks",
        description=(
            "Create multiple ranger tasks in a single operation after operator approval. "
            "Use this to dispatch rebalancing, charging, or maintenance tasks in bulk. "
            "IMPORTANT: Always show the plan and get operator confirmation before calling this tool."
        ),
        parameters={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "List of task definitions to create",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_type": {
                                "type": "string",
                                "description": "'charging' | 'rebalancing' | 'maintenance' | 'inspection'",
                            },
                            "vehicle_id": {
                                "type": "string",
                                "description": "Vehicle to assign (optional)",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Instructions for the ranger",
                            },
                            "priority": {
                                "type": "string",
                                "description": "'low' | 'medium' | 'high' | 'urgent' (default: 'medium')",
                            },
                        },
                        "required": ["task_type"],
                    },
                },
            },
            "required": ["tasks"],
        },
        function=_batch_tasks_wrapper,
        tool_category="action",
    )

    registry.register_tool(
        name="internal_micromobility_get_trip_performance",
        description=(
            "Compute trip performance KPIs for the last N days: total trips, completion rate, "
            "average duration and distance, revenue, peak hour, and top performing service areas. "
            "Use for operational reporting and trend analysis."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Lookback period in days (default 30)",
                },
            },
            "required": [],
        },
        function=_trip_performance_wrapper,
    )

    logger.info("Registered 6 Micromobility Intelligence tools")
