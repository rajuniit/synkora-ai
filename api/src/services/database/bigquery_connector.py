"""BigQuery connector using gcloud-aio-bigquery — native asyncio, no run_in_executor."""

import asyncio
import json
import logging
from io import StringIO
from typing import Any

import aiohttp

from src.models.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)

_SCHEMA_TABLE_LIMIT = 20
_POLL_INTERVAL = 2    # seconds between job-completion checks
_MAX_POLL_TIME = 300  # 5-minute query timeout


def _parse_bq_response(response: dict) -> dict[str, Any]:
    """Convert BigQuery REST getQueryResults response to our standard format."""
    schema = response.get("schema", {})
    fields = schema.get("fields", [])
    columns = [f["name"] for f in fields]

    raw_rows = response.get("rows", [])
    rows = []
    for raw_row in raw_rows:
        values = [cell.get("v") for cell in raw_row.get("f", [])]
        rows.append(dict(zip(columns, values)))

    return {
        "success": True,
        "rows": rows,
        "row_count": int(response.get("totalRows", len(rows))),
        "columns": columns,
    }


class BigQueryConnector:
    """
    Native async BigQuery connector backed by gcloud-aio-bigquery.

    Uses aiohttp under the hood — zero run_in_executor, zero thread-pool usage.
    Queries are submitted via the BigQuery jobs.query REST endpoint; long-running
    jobs are polled with ``asyncio.sleep`` between checks so the event loop is
    never blocked.

    Authentication is via a service account JSON dict stored in
    ``connection_params["service_account_json"]``.
    Project ID comes from ``connection_params["project_id"]`` or
    ``database_connection.database_name``.
    Dataset comes from ``connection_params.get("dataset")``.
    """

    def __init__(self, database_connection: DatabaseConnection) -> None:
        self.database_connection = database_connection
        self._conn_params: dict[str, Any] = database_connection.connection_params or {}
        self._project_id: str = (
            self._conn_params.get("project_id") or database_connection.database_name or ""
        )
        self._dataset: str | None = self._conn_params.get("dataset")
        self._location: str | None = self._conn_params.get("location")
        self._session: aiohttp.ClientSession | None = None
        self._service_account_json: dict | None = None
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        try:
            from gcloud.aio.bigquery import Job  # noqa: PLC0415
        except ImportError:
            logger.error(
                "gcloud-aio-bigquery is not installed. "
                "Add 'gcloud-aio-bigquery' to dependencies."
            )
            return False

        try:
            service_account_json: dict | None = self._conn_params.get("service_account_json")
            if not service_account_json:
                logger.error("connection_params['service_account_json'] is required for BigQuery")
                return False
            if not self._project_id:
                logger.error("BigQuery project_id must be set in connection_params or database_name")
                return False

            self._session = aiohttp.ClientSession()
            self._service_account_json = service_account_json
            self._connected = True

            logger.info(
                "Connected to BigQuery project=%s dataset=%s",
                self._project_id,
                self._dataset,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to BigQuery: %s", e)
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None
            self._connected = False
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._service_account_json = None

        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

        logger.info("Disconnected from BigQuery project=%s", self._project_id)

    def _make_job(self) -> Any:
        """Create a new Job instance for a single query with a fresh service file."""
        from gcloud.aio.bigquery import Job  # noqa: PLC0415

        # A new StringIO must be created each time — gcloud-aio-auth reads it
        # to EOF on the first token acquisition and will fall back to the GCP
        # metadata server if it receives an already-exhausted stream.
        service_file = StringIO(json.dumps(self._service_account_json))
        return Job(
            project=self._project_id,
            service_file=service_file,
            session=self._session,
            location=self._location,
        )

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(
        self, query: str, params: list[Any] | None = None  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Execute a BigQuery SQL query asynchronously.

        Submits the job via jobs.query and polls jobs.getQueryResults with
        ``asyncio.sleep`` between checks — the event loop is never blocked
        regardless of how long the query takes.

        Args:
            query: Standard SQL query string.
            params: Ignored (BigQuery uses named @params in the query string).

        Returns:
            Standard connector result dict.
        """
        if not self._connected:
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": "Not connected. Call connect() first.",
            }

        try:
            job = self._make_job()
            query_request: dict[str, Any] = {"query": query, "useLegacySql": False}
            if self._location:
                query_request["location"] = self._location

            # Submit the job — returns immediately; event loop stays free
            response = await job.query(query_request, timeout=60)

            # Fast path: job finished within initial request timeout
            if response.get("jobComplete"):
                return _parse_bq_response(response)

            # Slow path: poll until complete
            elapsed = 0
            while elapsed < _MAX_POLL_TIME:
                await asyncio.sleep(_POLL_INTERVAL)  # event loop free between polls
                elapsed += _POLL_INTERVAL

                response = await job.get_query_results()
                if response.get("jobComplete"):
                    return _parse_bq_response(response)

            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": f"Query timed out after {_MAX_POLL_TIME}s",
            }

        except Exception as e:
            logger.error("BigQuery query failed: %s", e)
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        details: dict[str, Any] = {
            "project": self._project_id,
            "dataset": self._dataset,
            "location": self._location,
        }
        try:
            connected = await self.connect()
            if not connected:
                return {
                    "success": False,
                    "message": "Failed to establish BigQuery connection",
                    "details": details,
                }
            result = await self.execute_query("SELECT 1 AS alive")
            if not result["success"]:
                return {
                    "success": False,
                    "message": result.get("error", "Query failed"),
                    "details": details,
                }
            return {"success": True, "message": "Connection successful", "details": details}
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {e}",
                "details": details,
            }
        finally:
            await self.disconnect()

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    async def get_tables(self) -> list[str]:
        if not self._dataset:
            logger.warning("No dataset configured; cannot list tables")
            return []

        result = await self.execute_query(
            f"SELECT table_name "
            f"FROM `{self._project_id}.{self._dataset}.INFORMATION_SCHEMA.TABLES` "
            f"WHERE table_type = 'BASE TABLE' "
            f"ORDER BY table_name"
        )
        if not result["success"]:
            logger.error("Failed to list BigQuery tables: %s", result.get("error"))
            return []
        return [row.get("table_name", "") for row in result["rows"] if row.get("table_name")]

    async def get_schema(self) -> dict[str, Any]:
        try:
            table_names = await self.get_tables()
            tables = []
            for name in table_names[:_SCHEMA_TABLE_LIMIT]:
                info = await self.get_table_info(name)
                tables.append({"name": name, "columns": info.get("columns", [])})
            return {"success": True, "tables": tables}
        except Exception as e:
            logger.error("Failed to get BigQuery schema: %s", e)
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        if not self._dataset:
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": "No dataset configured",
            }

        try:
            result = await self.execute_query(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM `{self._project_id}.{self._dataset}.INFORMATION_SCHEMA.COLUMNS` "
                f"WHERE table_name = '{table_name}' "
                f"ORDER BY ordinal_position"
            )
            if not result["success"]:
                return {
                    "success": False,
                    "table_name": table_name,
                    "columns": [],
                    "error": result.get("error"),
                }

            columns = [
                {
                    "name": row.get("column_name", ""),
                    "type": row.get("data_type", ""),
                    "nullable": row.get("is_nullable", "YES") == "YES",
                }
                for row in result["rows"]
            ]
            return {"success": True, "table_name": table_name, "columns": columns}

        except Exception as e:
            logger.error("Failed to get BigQuery table info for '%s': %s", table_name, e)
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": str(e),
            }
