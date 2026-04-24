"""Snowflake database connector using snowflake-connector-python.

All blocking Snowflake connector calls are wrapped in run_in_executor so the
async event loop is never blocked.
"""

import asyncio
import logging
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class SnowflakeConnector:
    """
    Snowflake connector that wraps the synchronous snowflake-connector-python
    library in asyncio executor calls.

    Mirrors the interface of PostgreSQLConnector / MySQLConnector so existing
    callers can treat it interchangeably.
    """

    def __init__(self, database_connection: DatabaseConnection):
        """
        Initialize Snowflake connector.

        Args:
            database_connection: DatabaseConnection model instance. Expected fields:
                - host or connection_params["account"]: Snowflake account identifier
                - database_name: Snowflake database
                - username: Snowflake user
                - password_encrypted: Fernet-encrypted password
                - connection_params.get("warehouse"): virtual warehouse
                - connection_params.get("schema_name", "PUBLIC"): schema
                - connection_params.get("role"): optional Snowflake role
        """
        self.database_connection = database_connection
        self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_account(self) -> str:
        """Resolve the Snowflake account identifier from the model."""
        conn_params = self.database_connection.connection_params or {}
        # Prefer explicit "account" key in connection_params; fall back to host.
        return conn_params.get("account") or self.database_connection.host or ""

    def _get_schema(self) -> str:
        conn_params = self.database_connection.connection_params or {}
        return conn_params.get("schema_name", "PUBLIC")

    def _get_warehouse(self) -> str | None:
        conn_params = self.database_connection.connection_params or {}
        return conn_params.get("warehouse")

    def _get_role(self) -> str | None:
        conn_params = self.database_connection.connection_params or {}
        return conn_params.get("role")

    def _run_sync(self, fn, *args, **kwargs):
        """Run a synchronous callable in the default executor."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Establish a Snowflake connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            import snowflake.connector  # noqa: PLC0415  (deferred, optional dep)
        except ImportError:
            logger.error(
                "snowflake-connector-python is not installed. Add 'snowflake-connector-python' to dependencies."
            )
            return False

        try:
            password = decrypt_value(self.database_connection.password_encrypted)
            account = self._get_account()
            warehouse = self._get_warehouse()
            role = self._get_role()

            connect_kwargs: dict[str, Any] = {
                "account": account,
                "user": self.database_connection.username,
                "password": password,
                "database": self.database_connection.database_name,
                "schema": self._get_schema(),
            }
            if warehouse:
                connect_kwargs["warehouse"] = warehouse
            if role:
                connect_kwargs["role"] = role

            def _do_connect():
                conn = snowflake.connector.connect(**connect_kwargs)
                return conn

            self._conn = await self._run_sync(_do_connect)

            logger.info(f"Connected to Snowflake account={account} database={self.database_connection.database_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            return False

    async def disconnect(self) -> None:
        """Close the Snowflake connection."""
        if self._conn is not None:
            try:
                conn = self._conn
                self._conn = None
                await self._run_sync(conn.close)
                logger.info("Disconnected from Snowflake")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(self, query: str, params=None) -> dict[str, Any]:
        """
        Execute a Snowflake query using the async job API.

        Three distinct executor calls — each held for milliseconds:
          1. execute_async() — submits the job, returns query_id immediately.
          2. get_query_status_throw_if_error() — fast status check, called in a
             loop with ``asyncio.sleep`` between iterations so the event loop
             is completely free while the warehouse processes the query.
          3. get_results_from_sfqid() + fetchall() — fetches already-ready data.

        Args:
            query: SQL query string (%s placeholders for bind params).
            params: Optional sequence of bind parameters.

        Returns:
            Standard connector result dict.
        """
        if self._conn is None:
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": "Not connected. Call connect() first.",
            }

        loop = asyncio.get_event_loop()
        _MAX_WAIT = 300  # 5-minute hard limit

        # Step 1: submit async — brief sync call (~ms), returns query_id
        def _submit():
            cur = self._conn.cursor()
            if params:
                cur.execute_async(query, params)
            else:
                cur.execute_async(query)
            return cur.sfqid, cur

        try:
            query_id, cursor = await loop.run_in_executor(None, _submit)
        except Exception as e:
            logger.error(f"Snowflake query submission failed: {e}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

        # Step 2: poll status — each check is a brief HTTP call (~ms)
        # asyncio.sleep() between checks keeps the event loop fully free
        elapsed = 0
        try:
            while elapsed < _MAX_WAIT:

                def _check(qid=query_id):
                    status = self._conn.get_query_status_throw_if_error(qid)
                    return self._conn.is_still_running(status)

                still_running = await loop.run_in_executor(None, _check)
                if not still_running:
                    break
                await asyncio.sleep(1)  # event loop completely free here
                elapsed += 1
            else:
                return {
                    "success": False,
                    "rows": [],
                    "row_count": 0,
                    "columns": [],
                    "error": f"Query timed out after {_MAX_WAIT}s",
                }
        except Exception as e:
            logger.error(f"Snowflake query status check failed: {e}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

        # Step 3: fetch results — query already done, this call is fast
        def _fetch(cur=cursor, qid=query_id):
            cur.get_results_from_sfqid(qid)
            rows_raw = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [dict(zip(columns, row, strict=False)) for row in rows_raw]
            cur.close()
            return {"success": True, "rows": rows, "row_count": len(rows), "columns": columns}

        try:
            return await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.error(f"Snowflake result fetch failed: {e}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        """
        Test connectivity by querying Snowflake system functions.

        Returns:
            {
                "success": bool,
                "message": str,
                "details": {
                    "version": str,
                    "database": str,
                    "warehouse": str | None,
                    "account": str
                }
            }
        """
        connected = await self.connect()
        if not connected:
            return {"success": False, "message": "Failed to establish Snowflake connection", "details": {}}

        try:
            version_result = await self.execute_query("SELECT CURRENT_VERSION() AS version")
            db_result = await self.execute_query("SELECT CURRENT_DATABASE() AS database_name")
            wh_result = await self.execute_query("SELECT CURRENT_WAREHOUSE() AS warehouse")

            version = (
                version_result["rows"][0].get("VERSION", "unknown")
                if version_result.get("success") and version_result["rows"]
                else "unknown"
            )
            database = (
                db_result["rows"][0].get("DATABASE_NAME", self.database_connection.database_name)
                if db_result.get("success") and db_result["rows"]
                else self.database_connection.database_name
            )
            warehouse = (
                wh_result["rows"][0].get("WAREHOUSE") if wh_result.get("success") and wh_result["rows"] else None
            )

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": version,
                    "database": database,
                    "warehouse": warehouse,
                    "account": self._get_account(),
                },
            }
        except Exception as e:
            logger.error(f"Snowflake connection test failed: {e}")
            return {"success": False, "message": f"Connection test failed: {e}", "details": {}}
        finally:
            await self.disconnect()

    async def get_tables(self) -> list[str]:
        """
        Return a list of base table names in the current schema from INFORMATION_SCHEMA.

        Returns:
            List of table name strings, empty on error.
        """
        schema = self._get_schema()
        result = await self.execute_query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
            "ORDER BY TABLE_NAME",
            (schema,),
        )
        if not result.get("success"):
            logger.error(f"Failed to list Snowflake tables: {result.get('error')}")
            return []
        return [row.get("TABLE_NAME", "") for row in result.get("rows", []) if row.get("TABLE_NAME")]

    async def get_schema(self) -> dict[str, Any]:
        """
        Return schema metadata for up to 20 tables including column details.

        Returns:
            {
                "success": bool,
                "tables": list[{"name": str, "columns": list[dict]}],
                "error": str   # only on failure
            }
        """
        try:
            tables = await self.get_tables()
            schema_name = self._get_schema()
            table_info = []

            for table in tables[:20]:
                cols_result = await self.execute_query(
                    "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
                    "FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                    "ORDER BY ORDINAL_POSITION",
                    (schema_name, table),
                )
                columns = cols_result.get("rows", []) if cols_result.get("success") else []
                table_info.append({"name": table, "columns": columns})

            return {"success": True, "tables": table_info}
        except Exception as e:
            logger.error(f"Failed to get Snowflake schema: {e}")
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Return column metadata for a specific table.

        Args:
            table_name: Unquoted table name.

        Returns:
            {
                "success": bool,
                "table_name": str,
                "columns": list[dict],
                "error": str   # only on failure
            }
        """
        schema_name = self._get_schema()
        result = await self.execute_query(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            (schema_name, table_name),
        )
        return {
            "success": result.get("success", False),
            "table_name": table_name,
            "columns": result.get("rows", []),
            **({"error": result["error"]} if not result.get("success") and "error" in result else {}),
        }
