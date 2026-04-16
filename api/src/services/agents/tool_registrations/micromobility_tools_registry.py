"""
Micromobility Tools Registry

Registers all Dashboard micromobility tools with the ADK tool registry.
Covers vehicles, trips, riders, ranger tasks, fleets, areas, pricing,
promotions, invoices, analytics, and reports.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_micromobility_tools(registry):
    """
    Register all micromobility tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.micromobility_tools import (
        internal_micromobility_adjust_rider_balance,
        internal_micromobility_analytics_activity,
        internal_micromobility_analytics_overview,
        internal_micromobility_cancel_trip,
        internal_micromobility_complete_trip,
        internal_micromobility_create_task,
        internal_micromobility_get_promotion,
        internal_micromobility_get_report,
        internal_micromobility_get_rider,
        internal_micromobility_get_task,
        internal_micromobility_get_trip,
        internal_micromobility_get_vehicle,
        internal_micromobility_list_fleets,
        internal_micromobility_list_invoices,
        internal_micromobility_list_parking_areas,
        internal_micromobility_list_pricing_plans,
        internal_micromobility_list_promotions,
        internal_micromobility_list_reports,
        internal_micromobility_list_riders,
        internal_micromobility_list_service_areas,
        internal_micromobility_list_tasks,
        internal_micromobility_list_trips,
        internal_micromobility_list_vehicles,
        internal_micromobility_lock_vehicle,
        internal_micromobility_refund_invoice,
        internal_micromobility_sync_vehicle_status,
        internal_micromobility_unlock_vehicle,
        internal_micromobility_update_task,
    )

    # ── Vehicle Wrappers ──────────────────────────────────────────────────────

    async def internal_micromobility_list_vehicles_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_vehicles(
            config=config,
            runtime_context=runtime_context,
            search=kwargs.get("search"),
            status=kwargs.get("status"),
            fleet_id=kwargs.get("fleet_id"),
            service_area_id=kwargs.get("service_area_id"),
            fetch_test_vehicles=kwargs.get("fetch_test_vehicles"),
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_get_vehicle_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_vehicle(
            config=config,
            runtime_context=runtime_context,
            vehicle_id=kwargs.get("vehicle_id", ""),
        )

    async def internal_micromobility_lock_vehicle_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_lock_vehicle(
            config=config,
            runtime_context=runtime_context,
            vehicle_id=kwargs.get("vehicle_id", ""),
        )

    async def internal_micromobility_unlock_vehicle_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_unlock_vehicle(
            config=config,
            runtime_context=runtime_context,
            vehicle_id=kwargs.get("vehicle_id", ""),
        )

    async def internal_micromobility_sync_vehicle_status_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_sync_vehicle_status(
            config=config,
            runtime_context=runtime_context,
            vehicle_id=kwargs.get("vehicle_id", ""),
        )

    # ── Trip Wrappers ─────────────────────────────────────────────────────────

    async def internal_micromobility_list_trips_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_trips(
            config=config,
            runtime_context=runtime_context,
            status=kwargs.get("status"),
            vehicle_id=kwargs.get("vehicle_id"),
            rider_id=kwargs.get("rider_id"),
            fleet_id=kwargs.get("fleet_id"),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_get_trip_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_trip(
            config=config,
            runtime_context=runtime_context,
            trip_id=kwargs.get("trip_id", ""),
        )

    async def internal_micromobility_cancel_trip_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_cancel_trip(
            config=config,
            runtime_context=runtime_context,
            trip_id=kwargs.get("trip_id", ""),
        )

    async def internal_micromobility_complete_trip_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_complete_trip(
            config=config,
            runtime_context=runtime_context,
            trip_id=kwargs.get("trip_id", ""),
        )

    # ── Rider Wrappers ────────────────────────────────────────────────────────

    async def internal_micromobility_list_riders_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_riders(
            config=config,
            runtime_context=runtime_context,
            search=kwargs.get("search"),
            status=kwargs.get("status"),
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_get_rider_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_rider(
            config=config,
            runtime_context=runtime_context,
            rider_id=kwargs.get("rider_id", ""),
        )

    async def internal_micromobility_adjust_rider_balance_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_adjust_rider_balance(
            config=config,
            runtime_context=runtime_context,
            rider_id=kwargs.get("rider_id", ""),
            amount=float(kwargs.get("amount")),
            note=kwargs.get("note"),
        )

    # ── Ranger Task Wrappers ──────────────────────────────────────────────────

    async def internal_micromobility_list_tasks_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_tasks(
            config=config,
            runtime_context=runtime_context,
            status=kwargs.get("status"),
            task_type=kwargs.get("task_type"),
            operator_id=kwargs.get("operator_id"),
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_get_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_task(
            config=config,
            runtime_context=runtime_context,
            task_id=kwargs.get("task_id", ""),
        )

    async def internal_micromobility_create_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_create_task(
            config=config,
            runtime_context=runtime_context,
            task_type=kwargs.get("task_type", ""),
            vehicle_id=kwargs.get("vehicle_id"),
            operator_id=kwargs.get("operator_id"),
            notes=kwargs.get("notes"),
            priority=kwargs.get("priority"),
        )

    async def internal_micromobility_update_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_update_task(
            config=config,
            runtime_context=runtime_context,
            task_id=kwargs.get("task_id", ""),
            status=kwargs.get("status"),
            notes=kwargs.get("notes"),
        )

    # ── Fleet & Area Wrappers ─────────────────────────────────────────────────

    async def internal_micromobility_list_fleets_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_fleets(config=config, runtime_context=runtime_context)

    async def internal_micromobility_list_service_areas_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_service_areas(
            config=config,
            runtime_context=runtime_context,
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_list_parking_areas_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_parking_areas(config=config, runtime_context=runtime_context)

    # ── Pricing & Promotion Wrappers ──────────────────────────────────────────

    async def internal_micromobility_list_pricing_plans_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_pricing_plans(
            config=config,
            runtime_context=runtime_context,
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_list_promotions_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_promotions(config=config, runtime_context=runtime_context)

    async def internal_micromobility_get_promotion_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_promotion(
            config=config,
            runtime_context=runtime_context,
            promotion_id=kwargs.get("promotion_id", ""),
        )

    # ── Invoice Wrappers ──────────────────────────────────────────────────────

    async def internal_micromobility_list_invoices_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_invoices(
            config=config,
            runtime_context=runtime_context,
            rider_id=kwargs.get("rider_id"),
            trip_id=kwargs.get("trip_id"),
            limit=kwargs.get("limit"),
            offset=kwargs.get("offset"),
        )

    async def internal_micromobility_refund_invoice_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_refund_invoice(
            config=config,
            runtime_context=runtime_context,
            invoice_id=kwargs.get("invoice_id", ""),
            reason=kwargs.get("reason"),
        )

    # ── Analytics Wrappers ────────────────────────────────────────────────────

    async def internal_micromobility_analytics_overview_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_analytics_overview(
            config=config,
            runtime_context=runtime_context,
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            fleet_id=kwargs.get("fleet_id"),
            chart_type=kwargs.get("chart_type"),
        )

    async def internal_micromobility_analytics_activity_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_analytics_activity(
            config=config,
            runtime_context=runtime_context,
            start_hour=kwargs.get("start_hour"),
            step_hour=kwargs.get("step_hour"),
        )

    # ── Report Wrappers ───────────────────────────────────────────────────────

    async def internal_micromobility_list_reports_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_list_reports(config=config, runtime_context=runtime_context)

    async def internal_micromobility_get_report_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_micromobility_get_report(
            config=config,
            runtime_context=runtime_context,
            report_id=kwargs.get("report_id", ""),
        )

    # ── Register Vehicle Tools ────────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_vehicles",
        description=(
            "List vehicles in the micromobility fleet. Filter by status, fleet, or service area. "
            "Returns vehicle ID, type, battery level, GPS location, and current status."
        ),
        parameters={
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by vehicle ID, serial number, or QR code"},
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'available', 'in_use', 'maintenance', 'reserved', 'offline'",
                },
                "fleet_id": {"type": "string", "description": "Filter by fleet ID"},
                "service_area_id": {"type": "string", "description": "Filter by service area ID"},
                "fetch_test_vehicles": {
                    "type": "boolean",
                    "description": "Include test/sandbox vehicles",
                },
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_vehicles_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_vehicle",
        description=(
            "Get full details for a specific vehicle including battery level, GPS coordinates, "
            "lock status, fleet assignment, and recent trip history."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle ID"},
            },
            "required": ["vehicle_id"],
        },
        function=internal_micromobility_get_vehicle_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_lock_vehicle",
        description=(
            "Remotely lock a vehicle via the IoT command. "
            "Use to secure a vehicle that is not in an active trip. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle ID to lock"},
            },
            "required": ["vehicle_id"],
        },
        function=internal_micromobility_lock_vehicle_wrapper,
        tool_category="action",
    )

    registry.register_tool(
        name="internal_micromobility_unlock_vehicle",
        description=(
            "Remotely unlock a vehicle via the IoT command. "
            "Use to start a trip or assist a stuck rider. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle ID to unlock"},
            },
            "required": ["vehicle_id"],
        },
        function=internal_micromobility_unlock_vehicle_wrapper,
        tool_category="action",
    )

    registry.register_tool(
        name="internal_micromobility_sync_vehicle_status",
        description=(
            "Force sync a vehicle's status from the IoT device to the platform. "
            "Use when the displayed status appears stale or out of sync. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string", "description": "Vehicle ID to sync"},
            },
            "required": ["vehicle_id"],
        },
        function=internal_micromobility_sync_vehicle_status_wrapper,
        tool_category="action",
    )

    # ── Register Trip Tools ───────────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_trips",
        description=(
            "List trips with optional filtering by status, vehicle, rider, fleet, or date range. "
            "Returns trip duration, distance, cost, start/end locations."
        ),
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'active', 'completed', 'cancelled'",
                },
                "vehicle_id": {"type": "string", "description": "Filter by vehicle ID"},
                "rider_id": {"type": "string", "description": "Filter by rider ID"},
                "fleet_id": {"type": "string", "description": "Filter by fleet ID"},
                "start_date": {"type": "string", "description": "Filter from date (ISO 8601, e.g. 2026-04-01)"},
                "end_date": {"type": "string", "description": "Filter to date (ISO 8601)"},
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_trips_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_trip",
        description=(
            "Get full details for a specific trip including route map, duration, distance, "
            "cost breakdown, rider info, and start/end timestamps."
        ),
        parameters={
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "Trip ID"},
            },
            "required": ["trip_id"],
        },
        function=internal_micromobility_get_trip_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_cancel_trip",
        description=(
            "Cancel an active trip on the platform. "
            "Use when a rider is having trouble ending their trip or for operational issues. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "Trip ID to cancel"},
            },
            "required": ["trip_id"],
        },
        function=internal_micromobility_cancel_trip_wrapper,
        tool_category="action",
    )

    registry.register_tool(
        name="internal_micromobility_complete_trip",
        description=(
            "Force complete an active trip on the platform. "
            "Use when a rider cannot end their trip normally. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "Trip ID to complete"},
            },
            "required": ["trip_id"],
        },
        function=internal_micromobility_complete_trip_wrapper,
        tool_category="action",
    )

    # ── Register Rider Tools ──────────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_riders",
        description=(
            "List riders registered on the platform. Search by name, email, or phone number. "
            "Returns rider profile, balance, status, and trip count."
        ),
        parameters={
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by name, email, or phone number"},
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'active', 'inactive', 'suspended', 'pending'",
                },
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_riders_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_rider",
        description=(
            "Get full profile for a specific rider including wallet balance, trip history, "
            "account status, and payment methods."
        ),
        parameters={
            "type": "object",
            "properties": {
                "rider_id": {"type": "string", "description": "Rider ID"},
            },
            "required": ["rider_id"],
        },
        function=internal_micromobility_get_rider_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_adjust_rider_balance",
        description=(
            "Adjust a rider's wallet balance. Provide a positive amount to add credit, "
            "negative to deduct. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "rider_id": {"type": "string", "description": "Rider ID"},
                "amount": {
                    "type": "number",
                    "description": "Amount to add (positive) or deduct (negative) from rider wallet",
                },
                "note": {"type": "string", "description": "Optional reason or note for the adjustment"},
            },
            "required": ["rider_id", "amount"],
        },
        function=internal_micromobility_adjust_rider_balance_wrapper,
        tool_category="action",
    )

    # ── Register Ranger Task Tools ────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_tasks",
        description=(
            "List ranger/operator tasks (charging, rebalancing, maintenance). "
            "Filter by status, task type, or assigned operator."
        ),
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'pending', 'in_progress', 'completed', 'cancelled'",
                },
                "task_type": {
                    "type": "string",
                    "description": "Filter by type: 'charging', 'rebalancing', 'maintenance', 'inspection'",
                },
                "operator_id": {"type": "string", "description": "Filter by assigned operator/ranger ID"},
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_tasks_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_task",
        description="Get full details for a specific ranger task including assigned operator, vehicle, and status history.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
        function=internal_micromobility_get_task_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_create_task",
        description=(
            "Create a new ranger task (e.g., charging, rebalancing, maintenance). "
            "Can assign to a specific vehicle and operator. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Task type: 'charging', 'rebalancing', 'maintenance', 'inspection'",
                },
                "vehicle_id": {"type": "string", "description": "Vehicle ID to assign the task to (optional)"},
                "operator_id": {"type": "string", "description": "Operator/ranger ID to assign (optional)"},
                "notes": {"type": "string", "description": "Additional notes or instructions"},
                "priority": {
                    "type": "string",
                    "description": "Priority level: 'low', 'medium', 'high', 'urgent'",
                },
            },
            "required": ["task_type"],
        },
        function=internal_micromobility_create_task_wrapper,
        tool_category="action",
    )

    registry.register_tool(
        name="internal_micromobility_update_task",
        description="Update a ranger task's status or notes. Use to mark tasks in progress or completed. Requires confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to update"},
                "status": {
                    "type": "string",
                    "description": "New status: 'pending', 'in_progress', 'completed', 'cancelled'",
                },
                "notes": {"type": "string", "description": "Updated notes or comments"},
            },
            "required": ["task_id"],
        },
        function=internal_micromobility_update_task_wrapper,
        tool_category="action",
    )

    # ── Register Fleet & Area Tools ───────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_fleets",
        description="List all fleets in the organization. Returns fleet name, vehicle count, and service area assignments.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_micromobility_list_fleets_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_list_service_areas",
        description=(
            "List operational service areas (zones) including geo-boundaries, speed limits, "
            "and zone type (operational, parking, no-ride, slow-speed)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_service_areas_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_list_parking_areas",
        description="List all designated parking areas and hubs including location, capacity, and type.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_micromobility_list_parking_areas_wrapper,
    )

    # ── Register Pricing & Promotion Tools ────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_pricing_plans",
        description=(
            "List all pricing plans including unlock fees, per-minute rates, day passes, and subscription plans."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_pricing_plans_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_list_promotions",
        description="List all promotions including discount codes, free ride offers, and referral bonuses.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_micromobility_list_promotions_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_promotion",
        description="Get details for a specific promotion including redemption count, eligibility, and expiry.",
        parameters={
            "type": "object",
            "properties": {
                "promotion_id": {"type": "string", "description": "Promotion ID"},
            },
            "required": ["promotion_id"],
        },
        function=internal_micromobility_get_promotion_wrapper,
    )

    # ── Register Invoice Tools ────────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_invoices",
        description=(
            "List transaction invoices with optional filtering by rider or trip. "
            "Returns amount, status, payment method, and timestamp."
        ),
        parameters={
            "type": "object",
            "properties": {
                "rider_id": {"type": "string", "description": "Filter by rider ID"},
                "trip_id": {"type": "string", "description": "Filter by trip ID"},
                "limit": {"type": "integer", "description": "Page size"},
                "offset": {"type": "integer", "description": "Pagination offset"},
            },
            "required": [],
        },
        function=internal_micromobility_list_invoices_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_refund_invoice",
        description=(
            "Issue a refund for a transaction invoice. "
            "Use for disputed charges, failed trips, or goodwill adjustments. Requires confirmation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "Invoice ID to refund"},
                "reason": {"type": "string", "description": "Reason for the refund (optional)"},
            },
            "required": ["invoice_id"],
        },
        function=internal_micromobility_refund_invoice_wrapper,
        tool_category="action",
    )

    # ── Register Analytics Tools ──────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_analytics_overview",
        description=(
            "Get analytics chart data (trips, revenue, active users) for a date range. "
            "chart_type is required: 'line' for trends over time, 'bar' for comparisons, 'gauge' for KPI snapshots."
        ),
        parameters={
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "description": "Chart type — must be one of: 'line', 'bar', 'gauge'",
                },
                "start_date": {"type": "string", "description": "Start date in ISO 8601 format (e.g. 2026-04-01)"},
                "end_date": {"type": "string", "description": "End date in ISO 8601 format"},
                "fleet_id": {"type": "string", "description": "Filter by fleet ID"},
            },
            "required": ["chart_type"],
        },
        function=internal_micromobility_analytics_overview_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_analytics_activity",
        description=(
            "Get hourly activity data showing peak usage hours across the day. "
            "Useful for identifying busy periods and optimizing fleet deployment."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_hour": {
                    "type": "integer",
                    "description": "Starting hour of the day (0-23)",
                },
                "step_hour": {
                    "type": "integer",
                    "description": "Time step in hours for grouping",
                },
            },
            "required": [],
        },
        function=internal_micromobility_analytics_activity_wrapper,
    )

    # ── Register Report Tools ─────────────────────────────────────────────────

    registry.register_tool(
        name="internal_micromobility_list_reports",
        description="List all generated reports available in the Dashboard (daily summaries, compliance, maintenance, etc.).",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_micromobility_list_reports_wrapper,
    )

    registry.register_tool(
        name="internal_micromobility_get_report",
        description="Get a specific report by ID including full data, summary statistics, and download links.",
        parameters={
            "type": "object",
            "properties": {
                "report_id": {"type": "string", "description": "Report ID"},
            },
            "required": ["report_id"],
        },
        function=internal_micromobility_get_report_wrapper,
    )

    logger.info(
        "Registered 28 micromobility tools (5 vehicle + 4 trip + 3 rider + 4 task + 3 area + 3 pricing + 2 invoice + 2 analytics + 2 report)"
    )
