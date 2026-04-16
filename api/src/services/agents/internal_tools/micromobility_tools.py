"""
Micromobility Dashboard Tools.

Provides tools for managing a micromobility fleet via the Dashboard API.
Covers vehicles, trips, riders, ranger tasks, analytics, reports, areas, pricing,
promotions, and invoices.

Auth: JWT Bearer token stored as api_token in OAuthApp (auth_method='api_token').
All endpoint paths are configurable via OAuthApp.config.endpoints.
"""

import base64
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# API endpoint defaults — all overridable via config.endpoints
ENDPOINT_DEFAULTS: dict[str, str] = {
    # Vehicles
    "list_vehicles": "/vehicles/",
    "get_vehicle": "/vehicles/{vehicle_id}/",
    "lock_vehicle": "/vehicles/{vehicle_id}/lock/",
    "unlock_vehicle": "/vehicles/{vehicle_id}/unlock/",
    "sync_vehicle_status": "/vehicles/{vehicle_id}/force-status-sync/",
    "update_vehicle": "/vehicles/{vehicle_id}/",
    "vehicle_lock_status": "/vehicles/{vehicle_id}/status/",
    # Trips
    "list_trips": "/trips/",
    "get_trip": "/trips/{trip_id}/",
    "cancel_trip": "/trips/{trip_id}/cancel/",
    "complete_trip": "/trips/{trip_id}/complete/",
    # Riders
    "list_riders": "/riders/",
    "get_rider": "/riders/{rider_id}/",
    "adjust_rider_balance": "/riders/{rider_id}/",
    "get_rider_payment_info": "/riders/{rider_id}/payment-info/",
    # Ranger Tasks
    "list_tasks": "/tasks/",
    "get_task": "/tasks/{task_id}/",
    "create_task": "/tasks/",
    "update_task": "/tasks/{task_id}/",
    # Fleets
    "list_fleets": "/fleets/",
    "get_fleet": "/fleets/{fleet_id}/",
    # Areas
    "list_service_areas": "/service-areas/",
    "get_service_area": "/service-areas/{service_area_id}/",
    "list_parking_areas": "/parking-areas/",
    "get_parking_area": "/parking-areas/{parking_area_id}/",
    # Pricing & Promotions
    "list_pricing_plans": "/pricing-plans/",
    "get_pricing_plan": "/pricing-plans/{pricing_plan_id}/",
    "list_promotions": "/promotions/",
    "get_promotion": "/promotions/{promotion_id}/",
    "notify_riders_promotion": "/promotions/{promotion_id}/notify-riders/",
    # Invoices
    "list_invoices": "/invoices/",
    "refund_invoice": "/invoices/{invoice_id}/refund/",
    # Analytics
    "analytics_line_chart": "/analytics/line-chart",
    "analytics_bar_chart": "/analytics/bar-chart",
    "analytics_gauge_chart": "/analytics/gauge-chart",
    "analytics_activity_chart": "/analytics/activity-chart/",
    "analytics_map_chart": "/analytics/map-chart",
    # Reports
    "list_reports": "/reports/",
    "get_report": "/reports/{report_id}/",
}

# Validation
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_id(value: str, field_name: str) -> str:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"Invalid {field_name}: must contain only alphanumeric characters, hyphens, and underscores")
    return value


def _validate_endpoint_path(path: str) -> str:
    if not path.startswith("/"):
        raise ValueError(f"Endpoint path must start with '/': {path!r}")
    if ".." in path:
        raise ValueError(f"Endpoint path must not contain '..': {path!r}")
    if "?" in path or "#" in path:
        raise ValueError(f"Endpoint path must not contain query params or fragments: {path!r}")
    return path


# ── Core helpers ─────────────────────────────────────────────────────────────


async def _get_micromobility_credentials(runtime_context: Any, tool_name: str) -> dict[str, Any]:
    if not runtime_context:
        raise ValueError("No runtime context. Please configure the micromobility integration in OAuth Apps.")

    from src.services.agents.credential_resolver import CredentialResolver

    resolver = CredentialResolver(runtime_context)
    credentials = await resolver.get_micromobility_credentials(tool_name)
    if not credentials:
        raise ValueError("micromobility not configured. Please connect your account in OAuth Apps settings.")
    return credentials


def _resolve_endpoint(mm_config: dict[str, Any], endpoint_key: str, **path_params: str) -> str:
    endpoints = mm_config.get("endpoints", {})
    raw_path = endpoints.get(endpoint_key) or ENDPOINT_DEFAULTS.get(endpoint_key)
    if not raw_path:
        raise ValueError(f"No endpoint configured for '{endpoint_key}'")
    _validate_endpoint_path(raw_path)
    safe_params = {k: _validate_id(v, k) for k, v in path_params.items()}
    try:
        return raw_path.format(**safe_params)
    except KeyError as e:
        raise ValueError(f"Missing path parameter {e} for endpoint '{endpoint_key}'") from e


async def _make_micromobility_request(
    method: str,
    endpoint: str,
    mm_config: dict[str, Any],
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from src.services.agents.internal_tools.web_tools import _is_url_safe

    base_url = mm_config.get("base_url", "").rstrip("/")
    auth_type = mm_config.get("auth_type")
    timeout = float(mm_config.get("request_timeout_seconds", 30))
    url = f"{base_url}{endpoint}"

    is_safe, ssrf_error = await _is_url_safe(url)
    if not is_safe:
        raise ValueError(f"Request blocked (SSRF protection): {ssrf_error}")
    if not url.startswith("https://"):
        raise ValueError("API base_url must use HTTPS")

    headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}

    if auth_type == "oauth":
        access_token = mm_config.get("access_token")
        if not access_token:
            raise ValueError("OAuth access token not available")
        headers["Authorization"] = f"Bearer {access_token}"
    elif auth_type == "api_key":
        api_token = mm_config.get("api_token")
        if not api_token:
            raise ValueError("API token not available")
        key_header = mm_config.get("api_key_header", "Authorization")
        key_format = mm_config.get("api_key_format", "Bearer {token}")
        headers[key_header] = key_format.format(token=api_token)
    elif auth_type == "basic_auth":
        username = mm_config.get("username")
        password = mm_config.get("password")
        if not username or not password:
            raise ValueError("Basic auth credentials not available")
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    else:
        raise ValueError(f"Unsupported auth_type: {auth_type!r}")

    for k, v in mm_config.get("custom_headers", {}).items():
        if k.lower() != "authorization":
            headers[k] = v

    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await client.request(
            method=method, url=url, headers=headers, params=params, json=json_data, timeout=timeout
        )

    if response.status_code == 429:
        return {
            "success": False,
            "error": f"Rate limit exceeded. Retry after: {response.headers.get('Retry-After', 'unknown')}",
            "status_code": 429,
        }

    # 401 with basic_auth: cached JWT has expired — re-login and retry once
    if response.status_code == 401 and mm_config.get("_login_url"):
        login_url = mm_config["_login_url"]
        username = mm_config["_login_username"]
        password = mm_config["_login_password"]
        token_field = mm_config["_login_token_field"]
        username_field = mm_config.get("_login_username_field", "username")
        password_field = mm_config.get("_login_password_field", "password")
        timeout = float(mm_config.get("request_timeout_seconds", 30))
        logger.info(f"JWT expired (401) — re-logging in via {login_url}")
        try:
            async with httpx.AsyncClient(follow_redirects=True) as refresh_client:
                login_resp = await refresh_client.post(
                    login_url,
                    json={username_field: username, password_field: password},
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    timeout=timeout,
                )
            if not login_resp.is_success:
                return {"success": False, "error": "JWT expired and re-login failed", "status_code": 401}
            new_token = login_resp.json().get(token_field)
            if not new_token:
                return {"success": False, "error": "JWT expired and re-login returned no token", "status_code": 401}
            # Update in-memory config and retry the original request once
            mm_config["api_token"] = new_token
            key_format = mm_config.get("api_key_format", "Bearer {token}")
            key_header = mm_config.get("api_key_header", "Authorization")
            headers[key_header] = key_format.format(token=new_token)
            async with httpx.AsyncClient(follow_redirects=False) as retry_client:
                response = await retry_client.request(
                    method=method, url=url, headers=headers, params=params, json=json_data, timeout=timeout
                )
            if not response.is_success:
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code} after token refresh",
                    "status_code": response.status_code,
                }
        except Exception as retry_err:
            logger.error(f"401 retry failed: {retry_err}")
            return {"success": False, "error": f"JWT expired and retry failed: {retry_err}", "status_code": 401}

    if not response.is_success:
        return {
            "success": False,
            "error": f"API request failed with status {response.status_code}",
            "status_code": response.status_code,
        }
    try:
        return {"success": True, "data": response.json(), "status_code": response.status_code}
    except Exception:
        return {"success": True, "data": response.text, "status_code": response.status_code}


# ── Vehicle Tools ─────────────────────────────────────────────────────────────


async def internal_micromobility_list_vehicles(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    search: str | None = None,
    status: str | None = None,
    fleet_id: str | None = None,
    service_area_id: str | None = None,
    fetch_test_vehicles: bool | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List fleet vehicles with optional search and filters."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_vehicles")
        endpoint = _resolve_endpoint(mm_config, "list_vehicles")
        params: dict[str, Any] = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if fleet_id:
            params["fleet"] = _validate_id(fleet_id, "fleet_id")
        if service_area_id:
            params["service_area"] = _validate_id(service_area_id, "service_area_id")
        if fetch_test_vehicles is not None:
            params["fetch_test_vehicles"] = fetch_test_vehicles
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_vehicles failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_vehicle(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    vehicle_id: str = "",
) -> dict[str, Any]:
    """Get full details for a specific vehicle."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_vehicle")
        endpoint = _resolve_endpoint(mm_config, "get_vehicle", vehicle_id=vehicle_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_vehicle failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_lock_vehicle(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    vehicle_id: str = "",
) -> dict[str, Any]:
    """Lock a vehicle remotely. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_lock_vehicle")
        endpoint = _resolve_endpoint(mm_config, "lock_vehicle", vehicle_id=vehicle_id)
        return await _make_micromobility_request("POST", endpoint, mm_config)
    except Exception as e:
        logger.error(f"lock_vehicle failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_unlock_vehicle(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    vehicle_id: str = "",
) -> dict[str, Any]:
    """Unlock a vehicle remotely. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_unlock_vehicle")
        endpoint = _resolve_endpoint(mm_config, "unlock_vehicle", vehicle_id=vehicle_id)
        return await _make_micromobility_request("POST", endpoint, mm_config)
    except Exception as e:
        logger.error(f"unlock_vehicle failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_sync_vehicle_status(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    vehicle_id: str = "",
) -> dict[str, Any]:
    """Force sync a vehicle's status from the IoT device. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_sync_vehicle_status")
        endpoint = _resolve_endpoint(mm_config, "sync_vehicle_status", vehicle_id=vehicle_id)
        return await _make_micromobility_request("POST", endpoint, mm_config)
    except Exception as e:
        logger.error(f"sync_vehicle_status failed: {e}")
        return {"success": False, "error": str(e)}


# ── Trip Tools ────────────────────────────────────────────────────────────────


async def internal_micromobility_list_trips(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    status: str | None = None,
    vehicle_id: str | None = None,
    rider_id: str | None = None,
    fleet_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List trips with optional filtering by status, vehicle, rider, or date range."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_trips")
        endpoint = _resolve_endpoint(mm_config, "list_trips")
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if vehicle_id:
            params["vehicle"] = _validate_id(vehicle_id, "vehicle_id")
        if rider_id:
            params["rider"] = _validate_id(rider_id, "rider_id")
        if fleet_id:
            params["fleet"] = _validate_id(fleet_id, "fleet_id")
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_trips failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_trip(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    trip_id: str = "",
) -> dict[str, Any]:
    """Get full details for a specific trip."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_trip")
        endpoint = _resolve_endpoint(mm_config, "get_trip", trip_id=trip_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_trip failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_cancel_trip(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    trip_id: str = "",
) -> dict[str, Any]:
    """Cancel an active trip. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_cancel_trip")
        endpoint = _resolve_endpoint(mm_config, "cancel_trip", trip_id=trip_id)
        return await _make_micromobility_request("POST", endpoint, mm_config)
    except Exception as e:
        logger.error(f"cancel_trip failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_complete_trip(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    trip_id: str = "",
) -> dict[str, Any]:
    """Force complete an active trip. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_complete_trip")
        endpoint = _resolve_endpoint(mm_config, "complete_trip", trip_id=trip_id)
        return await _make_micromobility_request("POST", endpoint, mm_config)
    except Exception as e:
        logger.error(f"complete_trip failed: {e}")
        return {"success": False, "error": str(e)}


# ── Rider Tools ───────────────────────────────────────────────────────────────


async def internal_micromobility_list_riders(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    search: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List riders with optional search by name, email, or phone."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_riders")
        endpoint = _resolve_endpoint(mm_config, "list_riders")
        params: dict[str, Any] = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_riders failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_rider(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    rider_id: str = "",
) -> dict[str, Any]:
    """Get full details for a specific rider including balance and status."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_rider")
        endpoint = _resolve_endpoint(mm_config, "get_rider", rider_id=rider_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_rider failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_adjust_rider_balance(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    rider_id: str = "",
    amount: float = 0.0,
    note: str | None = None,
) -> dict[str, Any]:
    """Adjust a rider's wallet balance (positive to add, negative to deduct). Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_adjust_rider_balance")
        endpoint = _resolve_endpoint(mm_config, "adjust_rider_balance", rider_id=rider_id)
        body: dict[str, Any] = {"balance": amount}
        if note:
            body["note"] = note
        return await _make_micromobility_request("POST", endpoint, mm_config, json_data=body)
    except Exception as e:
        logger.error(f"adjust_rider_balance failed: {e}")
        return {"success": False, "error": str(e)}


# ── Ranger Task Tools ─────────────────────────────────────────────────────────


async def internal_micromobility_list_tasks(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    status: str | None = None,
    task_type: str | None = None,
    operator_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List ranger tasks (charging, rebalancing, maintenance) with optional filters."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_tasks")
        endpoint = _resolve_endpoint(mm_config, "list_tasks")
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if task_type:
            params["task_type"] = task_type
        if operator_id:
            params["operator"] = _validate_id(operator_id, "operator_id")
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_tasks failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_task(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    task_id: str = "",
) -> dict[str, Any]:
    """Get details for a specific ranger task."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_task")
        endpoint = _resolve_endpoint(mm_config, "get_task", task_id=task_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_task failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_create_task(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    task_type: str = "",
    vehicle_id: str | None = None,
    operator_id: str | None = None,
    notes: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """Create a new ranger task (e.g., charging, rebalancing, maintenance). Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_create_task")
        endpoint = _resolve_endpoint(mm_config, "create_task")
        body: dict[str, Any] = {"task_type": task_type}
        if vehicle_id:
            body["vehicle"] = _validate_id(vehicle_id, "vehicle_id")
        if operator_id:
            body["operator"] = _validate_id(operator_id, "operator_id")
        if notes:
            body["notes"] = notes
        if priority:
            body["priority"] = priority
        return await _make_micromobility_request("POST", endpoint, mm_config, json_data=body)
    except Exception as e:
        logger.error(f"create_task failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_update_task(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    task_id: str = "",
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update a ranger task status or notes. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_update_task")
        endpoint = _resolve_endpoint(mm_config, "update_task", task_id=task_id)
        body: dict[str, Any] = {}
        if status:
            body["status"] = status
        if notes:
            body["notes"] = notes
        return await _make_micromobility_request("PATCH", endpoint, mm_config, json_data=body)
    except Exception as e:
        logger.error(f"update_task failed: {e}")
        return {"success": False, "error": str(e)}


# ── Fleet & Area Tools ────────────────────────────────────────────────────────


async def internal_micromobility_list_fleets(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
) -> dict[str, Any]:
    """List all fleets in the organization."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_fleets")
        endpoint = _resolve_endpoint(mm_config, "list_fleets")
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"list_fleets failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_list_service_areas(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List service areas (operational zones) with boundaries."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_service_areas")
        endpoint = _resolve_endpoint(mm_config, "list_service_areas")
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_service_areas failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_list_parking_areas(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
) -> dict[str, Any]:
    """List all parking areas/hubs."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_parking_areas")
        endpoint = _resolve_endpoint(mm_config, "list_parking_areas")
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"list_parking_areas failed: {e}")
        return {"success": False, "error": str(e)}


# ── Pricing & Promotion Tools ─────────────────────────────────────────────────


async def internal_micromobility_list_pricing_plans(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List all pricing plans."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_pricing_plans")
        endpoint = _resolve_endpoint(mm_config, "list_pricing_plans")
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_pricing_plans failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_list_promotions(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
) -> dict[str, Any]:
    """List all promotions (discounts, free rides, etc.)."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_promotions")
        endpoint = _resolve_endpoint(mm_config, "list_promotions")
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"list_promotions failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_promotion(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    promotion_id: str = "",
) -> dict[str, Any]:
    """Get details for a specific promotion."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_promotion")
        endpoint = _resolve_endpoint(mm_config, "get_promotion", promotion_id=promotion_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_promotion failed: {e}")
        return {"success": False, "error": str(e)}


# ── Invoice Tools ─────────────────────────────────────────────────────────────


async def internal_micromobility_list_invoices(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    rider_id: str | None = None,
    trip_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List transaction invoices with optional filtering."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_invoices")
        endpoint = _resolve_endpoint(mm_config, "list_invoices")
        params: dict[str, Any] = {}
        if rider_id:
            params["rider"] = _validate_id(rider_id, "rider_id")
        if trip_id:
            params["trip"] = _validate_id(trip_id, "trip_id")
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"list_invoices failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_refund_invoice(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    invoice_id: str = "",
    reason: str | None = None,
) -> dict[str, Any]:
    """Refund a transaction invoice. Requires HITL approval."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_refund_invoice")
        endpoint = _resolve_endpoint(mm_config, "refund_invoice", invoice_id=invoice_id)
        body: dict[str, Any] = {}
        if reason:
            body["reason"] = reason
        return await _make_micromobility_request("POST", endpoint, mm_config, json_data=body)
    except Exception as e:
        logger.error(f"refund_invoice failed: {e}")
        return {"success": False, "error": str(e)}


# ── Analytics Tools ───────────────────────────────────────────────────────────


async def internal_micromobility_analytics_overview(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    fleet_id: str | None = None,
    chart_type: str | None = None,
) -> dict[str, Any]:
    """
    Get analytics chart data (trips, revenue, users) for a date range.
    chart_type: 'line', 'bar', or 'gauge'. Required — must be specified by the caller.
    """
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_analytics_overview")
        key_map = {"line": "analytics_line_chart", "bar": "analytics_bar_chart", "gauge": "analytics_gauge_chart"}
        if not chart_type or chart_type not in key_map:
            return {"success": False, "error": f"chart_type must be one of: {list(key_map.keys())}"}
        endpoint_key = key_map[chart_type]
        endpoint = _resolve_endpoint(mm_config, endpoint_key)
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if fleet_id:
            params["fleet"] = _validate_id(fleet_id, "fleet_id")
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params)
    except Exception as e:
        logger.error(f"analytics_overview failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_analytics_activity(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    start_hour: int | None = None,
    step_hour: int | None = None,
) -> dict[str, Any]:
    """Get hourly activity chart data showing peak usage hours."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_analytics_activity")
        endpoint = _resolve_endpoint(mm_config, "analytics_activity_chart")
        params: dict[str, Any] = {}
        if start_hour is not None:
            params["start_hour"] = start_hour
        if step_hour is not None:
            params["step_hour"] = step_hour
        return await _make_micromobility_request("GET", endpoint, mm_config, params=params or None)
    except Exception as e:
        logger.error(f"analytics_activity failed: {e}")
        return {"success": False, "error": str(e)}


# ── Report Tools ──────────────────────────────────────────────────────────────


async def internal_micromobility_list_reports(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
) -> dict[str, Any]:
    """List all generated reports."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_list_reports")
        endpoint = _resolve_endpoint(mm_config, "list_reports")
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"list_reports failed: {e}")
        return {"success": False, "error": str(e)}


async def internal_micromobility_get_report(
    config: dict[str, Any] | None = None,
    runtime_context: Any | None = None,
    report_id: str = "",
) -> dict[str, Any]:
    """Get details and data for a specific report."""
    try:
        mm_config = await _get_micromobility_credentials(runtime_context, "internal_micromobility_get_report")
        endpoint = _resolve_endpoint(mm_config, "get_report", report_id=report_id)
        return await _make_micromobility_request("GET", endpoint, mm_config)
    except Exception as e:
        logger.error(f"get_report failed: {e}")
        return {"success": False, "error": str(e)}
