"""Datadog connector for metrics and logs queries."""

import asyncio
import functools
import json
import logging
import time
from datetime import UTC, datetime, timezone
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)

_SCHEMA_CACHE_TTL = 300  # 5 minutes


class DatadogConnector:
    """
    Datadog connector for querying metrics and logs.

    Connection fields (re-uses existing DatabaseConnection columns):
      password_encrypted -> API Key
      username           -> Application Key
      host               -> Site (e.g. datadoghq.com, datadoghq.eu)

    Query formats accepted by execute_query:
      Metrics: "avg:system.cpu.user{*}"
               "sum:trace.web.request{service:api} by {host}"
      Logs:    "logs: service:api status:error"
               '{"type": "logs", "query": "service:api", "from": "now-1h", "limit": 100}'
    """

    def __init__(self, database_connection: DatabaseConnection) -> None:
        self.database_connection = database_connection
        # Fix 3: single reused ApiClient (persistent HTTP connection pool)
        self._api_client: Any = None
        # Fix 2: schema result cache
        self._schema_cache: dict[str, Any] | None = None
        self._schema_cache_at: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_credentials(self) -> tuple[str, str, str]:
        """Return (api_key, app_key, site)."""
        api_key = ""
        if self.database_connection.password_encrypted:
            api_key = decrypt_value(self.database_connection.password_encrypted)
        app_key = self.database_connection.username or ""
        site = self.database_connection.host or "datadoghq.com"
        return api_key, app_key, site

    def _build_configuration(self) -> Any:
        from datadog_api_client import Configuration

        api_key, app_key, site = self._get_credentials()
        config = Configuration()
        config.api_key["apiKeyAuth"] = api_key
        if app_key:
            config.api_key["appKeyAuth"] = app_key
        config.server_variables["site"] = site
        return config

    def _ensure_client(self) -> Any:
        """
        Return the shared ApiClient, creating it on first call.

        Called from the async event-loop thread (never from the executor),
        so no threading races — asyncio is single-threaded between awaits.
        """
        if self._api_client is None:
            from datadog_api_client import ApiClient

            self._api_client = ApiClient(self._build_configuration())
        return self._api_client

    async def _run_sync(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Fix 1: run a synchronous SDK call in a thread-pool executor so it
        never blocks the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))

    @staticmethod
    def _unix_to_iso(t: int | float) -> str:
        return datetime.fromtimestamp(int(t), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        """Validate credentials by calling the Datadog /validate endpoint."""
        try:
            from datadog_api_client.v1.api.authentication_api import AuthenticationApi

            if not self._get_credentials()[0]:
                return {"success": False, "message": "API key is required"}

            client = self._ensure_client()

            def _validate() -> Any:
                return AuthenticationApi(client).validate()

            response = await self._run_sync(_validate)
            _, _, site = self._get_credentials()
            return {
                "success": True,
                "message": f"Connected to Datadog ({site})",
                "details": {"site": site, "valid": response.valid},
            }
        except Exception as e:
            logger.error("Datadog connection test failed: %s", e)
            return {"success": False, "message": f"Connection failed: {e}"}

    async def disconnect(self) -> None:
        """Close the shared HTTP connection pool."""
        if self._api_client is not None:
            try:
                self._api_client.rest_client.pool_manager.clear()
            except Exception:
                pass
            self._api_client = None
            self._schema_cache = None
            self._schema_cache_at = 0.0

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a metrics or logs query.

        Metrics: pass a DogStatsD-style query string, e.g. "avg:system.cpu.user{*}"
        Logs:    prefix the query with "logs: " or pass a JSON object with "type":"logs"
        """
        # Allow JSON envelope: {"type": "logs", "query": "...", "from": "...", "limit": 100}
        if query.strip().startswith("{"):
            try:
                parsed = json.loads(query)
                if parsed.get("type") == "logs":
                    return await self._query_logs(
                        parsed.get("query", "*"),
                        from_time=parsed.get("from", "now-1h"),
                        to_time=parsed.get("to", "now"),
                        limit=int(parsed.get("limit", 100)),
                    )
                # Fall through to metrics with "query" key
                query = parsed.get("query", query)
            except json.JSONDecodeError:
                pass

        if query.strip().lower().startswith("logs:"):
            log_query = query.strip()[5:].strip()
            from_time = params.get("from", "now-1h") if params else "now-1h"
            to_time = params.get("to", "now") if params else "now"
            limit = int(params.get("limit", 100)) if params else 100
            return await self._query_logs(log_query, from_time, to_time, limit)

        return await self._query_metrics(query, params)

    async def _query_metrics(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Query the Datadog Metrics API (v1)."""
        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi

            _from = int(params.get("from", 0)) if params else 0
            _to = int(params.get("to", 0)) if params else 0
            if not _from or not _to:
                _to = int(time.time())
                _from = _to - 3600

            client = self._ensure_client()

            def _query() -> Any:
                return MetricsApi(client).query_metrics(_from, _to, query)

            result = await self._run_sync(_query)
            result_dict = result.to_dict()

            rows = [
                {
                    "metric": s.get("metric"),
                    "display_name": s.get("display_name"),
                    "scope": s.get("scope"),
                    "points": s.get("pointlist") or [],
                }
                for s in (result_dict.get("series") or [])
            ]
            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "columns": ["metric", "display_name", "scope", "points"],
                "type": "metrics",
                "query": query,
            }
        except Exception as e:
            logger.error("Datadog metrics query failed: %s", e)
            return {"success": False, "error": str(e), "rows": [], "row_count": 0, "columns": []}

    async def _query_logs(
        self,
        query: str,
        from_time: str | int = "now-1h",
        to_time: str | int = "now",
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Fix 4: Query the Datadog Logs API (v2).

        query:     Datadog log search string, e.g. "service:api status:error"
        from_time: ISO-8601 string, relative ("now-1h"), or unix timestamp (int)
        to_time:   ISO-8601 string, relative ("now"), or unix timestamp (int)
        limit:     Max number of log events to return (capped at 1000)
        """
        try:
            from datadog_api_client.v2.api.logs_api import LogsApi
            from datadog_api_client.v2.model.logs_list_request import LogsListRequest
            from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
            from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
            from datadog_api_client.v2.model.logs_sort import LogsSort

            limit = min(limit, 1000)
            from_str = self._unix_to_iso(from_time) if isinstance(from_time, (int, float)) else str(from_time)
            to_str = self._unix_to_iso(to_time) if isinstance(to_time, (int, float)) else str(to_time)

            client = self._ensure_client()

            def _search() -> Any:
                body = LogsListRequest(
                    filter=LogsQueryFilter(query=query, _from=from_str, to=to_str),
                    sort=LogsSort.TIMESTAMP_DESCENDING,
                    page=LogsListRequestPage(limit=limit),
                )
                return LogsApi(client).list_logs(body=body)

            result = await self._run_sync(_search)

            rows = []
            for log in result.data or []:
                attrs = log.attributes
                # The Datadog v2 SDK raises AttributeError for missing optional fields.
                # Use getattr with fallbacks; also check the nested attributes dict.
                extra: dict[str, Any] = {}
                if hasattr(attrs, "attributes") and isinstance(attrs.attributes, dict):
                    extra = attrs.attributes
                message = getattr(attrs, "message", None) or extra.get("message") or extra.get("msg")
                rows.append(
                    {
                        "id": getattr(log, "id", None),
                        "timestamp": str(attrs.timestamp) if getattr(attrs, "timestamp", None) else None,
                        "message": message,
                        "service": getattr(attrs, "service", None) or extra.get("service"),
                        "status": getattr(attrs, "status", None) or extra.get("status"),
                        "host": getattr(attrs, "host", None) or extra.get("host"),
                        "tags": getattr(attrs, "tags", None) or [],
                    }
                )

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "columns": ["id", "timestamp", "message", "service", "status", "host", "tags"],
                "type": "logs",
                "query": query,
            }
        except Exception as e:
            logger.error("Datadog logs query failed: %s", e)
            return {"success": False, "error": str(e), "rows": [], "row_count": 0, "columns": []}

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    async def get_schema(self) -> dict[str, Any]:
        """
        Fix 2: Return available metrics and data types with a 5-minute TTL cache.

        Reduced lookback from 24 h → 1 h to avoid fetching thousands of metrics.
        Result is cached on the connector instance so repeated agent turns pay
        zero cost for the duration of the TTL.
        """
        now = time.monotonic()
        if self._schema_cache is not None and (now - self._schema_cache_at) < _SCHEMA_CACHE_TTL:
            return self._schema_cache

        try:
            from datadog_api_client.v1.api.metrics_api import MetricsApi

            since = int(time.time()) - 3600  # 1-hour lookback (was 24 h)
            client = self._ensure_client()

            def _list() -> Any:
                return MetricsApi(client).list_active_metrics(since)

            result = await self._run_sync(_list)
            metrics: list[str] = list(result.metrics or [])[:200]

            # Expose two queryable "tables": metrics and logs
            tables = [
                {
                    "name": "metrics",
                    "description": (
                        "Query with DogStatsD syntax, e.g. avg:system.cpu.user{*} or "
                        "sum:trace.web.request{service:api} by {host}. "
                        f"Active metrics sample: {', '.join(metrics[:30])}"
                    ),
                    "columns": [
                        {"name": "metric", "type": "string"},
                        {"name": "display_name", "type": "string"},
                        {"name": "scope", "type": "string"},
                        {"name": "points", "type": "array", "description": "[[unix_ts, value], ...]"},
                    ],
                },
                {
                    "name": "logs",
                    "description": (
                        "Query with: logs: <search>  — supports full Datadog log search syntax. "
                        "Examples: 'logs: service:api status:error', 'logs: @http.status_code:500'"
                    ),
                    "columns": [
                        {"name": "timestamp", "type": "datetime"},
                        {"name": "message", "type": "string"},
                        {"name": "service", "type": "string"},
                        {"name": "status", "type": "string"},
                        {"name": "host", "type": "string"},
                        {"name": "tags", "type": "array"},
                    ],
                },
            ]

            schema: dict[str, Any] = {
                "success": True,
                "tables": tables,
                "metrics": metrics,
            }
            self._schema_cache = schema
            self._schema_cache_at = now
            return schema

        except Exception as e:
            logger.error("Datadog schema fetch failed: %s", e)
            return {"success": False, "error": str(e), "tables": []}
