"""Databricks SQL connector for analytics queries."""

import logging
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class DatabricksConnector:
    """
    Databricks SQL connector using the Databricks SQL Connector for Python.

    Connection fields (re-uses existing DatabaseConnection columns):
      host               -> Server Hostname (e.g. workspace.cloud.databricks.com)
      database_path      -> HTTP Path (e.g. /sql/1.0/warehouses/xxx)
      password_encrypted -> Access Token
      database_name      -> Catalog (optional, default: 'main')
      username           -> Schema (optional, default: 'default')
    """

    def __init__(self, database_connection: DatabaseConnection):
        self.database_connection = database_connection

    def _get_config(self) -> dict[str, Any]:
        access_token = ""
        if self.database_connection.password_encrypted:
            access_token = decrypt_value(self.database_connection.password_encrypted)
        return {
            "server_hostname": self.database_connection.host or "",
            "http_path": self.database_connection.database_path or "",
            "access_token": access_token,
            "catalog": self.database_connection.database_name or "main",
            "schema": self.database_connection.username or "default",
        }

    async def test_connection(self) -> dict[str, Any]:
        """Test connection by opening a cursor and running SELECT 1."""
        import asyncio

        cfg = self._get_config()
        if not cfg["server_hostname"]:
            return {"success": False, "message": "Server hostname is required"}
        if not cfg["http_path"]:
            return {"success": False, "message": "HTTP path is required"}
        if not cfg["access_token"]:
            return {"success": False, "message": "Access token is required"}

        def _sync_test():
            from databricks import sql

            with sql.connect(
                server_hostname=cfg["server_hostname"],
                http_path=cfg["http_path"],
                access_token=cfg["access_token"],
                catalog=cfg["catalog"] or None,
                schema=cfg["schema"] or None,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

        try:
            await asyncio.get_event_loop().run_in_executor(None, _sync_test)
            return {
                "success": True,
                "message": f"Connected to Databricks ({cfg['server_hostname']})",
                "details": {
                    "server_hostname": cfg["server_hostname"],
                    "http_path": cfg["http_path"],
                    "catalog": cfg["catalog"],
                },
            }
        except Exception as e:
            logger.error(f"Databricks connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {e}"}

    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a SQL query and return results as rows + columns."""
        import asyncio

        cfg = self._get_config()

        def _sync_query():
            from databricks import sql

            with sql.connect(
                server_hostname=cfg["server_hostname"],
                http_path=cfg["http_path"],
                access_token=cfg["access_token"],
                catalog=cfg["catalog"] or None,
                schema=cfg["schema"] or None,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description or []]
                    return columns, [[str(v) if v is not None else None for v in row] for row in rows]

        try:
            columns, rows = await asyncio.get_event_loop().run_in_executor(None, _sync_query)
            return {"success": True, "columns": columns, "rows": rows, "row_count": len(rows)}
        except Exception as e:
            logger.error(f"Databricks query failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_schema(self) -> dict[str, Any]:
        """List tables in the configured catalog/schema."""
        return await self.execute_query("SHOW TABLES")
