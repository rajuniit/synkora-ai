"""Databricks connector for data analysis."""

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)

# SECURITY: Maximum allowed LIMIT value to prevent DoS
MAX_LIMIT = 10000
DEFAULT_LIMIT = 1000


def _validate_identifier(name: str) -> bool:
    """
    SECURITY: Validate a SQL identifier (catalog/schema/table name).

    Only allows alphanumeric characters and underscores.

    Args:
        name: The identifier to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))


def _sanitize_identifier(name: str) -> str:
    """
    SECURITY: Sanitize a SQL identifier for use in queries.

    Args:
        name: The identifier to sanitize

    Returns:
        Sanitized identifier with backticks

    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not _validate_identifier(name):
        raise ValueError(f"Invalid identifier: {name}")
    # Use backticks for Databricks SQL
    return f"`{name}`"


class DatabricksConnector(BaseConnector):
    """Connector for Databricks SQL and data analysis."""

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """Initialize Databricks connector.

        Args:
            data_source: DataSource model instance
            db: Database session
        """
        super().__init__(data_source, db)
        self.host = self.config.get("host")
        self.token = self.config.get("token")
        self.http_path = self.config.get("http_path")
        self.catalog = self.config.get("catalog", "main")
        self.schema = self.config.get("schema", "default")

    async def test_connection(self) -> dict[str, Any]:
        """Test connection to Databricks.

        Returns:
            Dict with success status and message
        """
        try:
            if not self.host or not self.token or not self.http_path:
                return {"success": False, "message": "Host, token, and HTTP path are required", "details": {}}

            # Test connection using Databricks SQL connector
            try:
                from databricks import sql
            except ImportError:
                return {
                    "success": False,
                    "message": "databricks-sql-connector package not installed. Install with: pip install databricks-sql-connector",
                    "details": {},
                }

            connection = sql.connect(server_hostname=self.host, http_path=self.http_path, access_token=self.token)

            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            connection.close()

            return {
                "success": True,
                "message": "Connection successful",
                "details": {"host": self.host, "catalog": self.catalog, "schema": self.schema},
            }

        except Exception as e:
            logger.error(f"Databricks connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {str(e)}", "details": {"error": str(e)}}

    async def execute_query(self, query: str, limit: int | None = None) -> dict[str, Any]:
        """Execute SQL query on Databricks.

        Args:
            query: SQL query to execute
            limit: Maximum number of rows to return

        Returns:
            Dict with query results
        """
        try:
            from databricks import sql

            connection = sql.connect(
                server_hostname=self.host,
                http_path=self.http_path,
                access_token=self.token,
                catalog=self.catalog,
                schema=self.schema,
            )

            cursor = connection.cursor()

            # SECURITY: Validate and sanitize LIMIT value to prevent SQL injection
            if limit is not None and "LIMIT" not in query.upper():
                # Ensure limit is a valid integer within bounds
                if isinstance(limit, int) and 1 <= limit <= MAX_LIMIT:
                    query = f"{query} LIMIT {int(limit)}"
                else:
                    query = f"{query} LIMIT {DEFAULT_LIMIT}"

            cursor.execute(query)

            # Fetch column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch results
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row, strict=False)))

            cursor.close()
            connection.close()

            return {"success": True, "data": results, "columns": columns, "row_count": len(results), "query": query}

        except Exception as e:
            logger.error(f"Failed to execute Databricks query: {e}")
            return {"success": False, "message": f"Query execution failed: {str(e)}", "error": str(e)}

    async def list_tables(self, catalog: str | None = None, schema: str | None = None) -> dict[str, Any]:
        """List tables in Databricks catalog.

        Args:
            catalog: Catalog name (default: from config)
            schema: Schema name (default: from config)

        Returns:
            Dict with table list
        """
        try:
            catalog = catalog or self.catalog
            schema = schema or self.schema

            # SECURITY: Validate and sanitize identifiers to prevent SQL injection
            safe_catalog = _sanitize_identifier(catalog)
            safe_schema = _sanitize_identifier(schema)

            query = f"SHOW TABLES IN {safe_catalog}.{safe_schema}"
            result = await self.execute_query(query)

            if result["success"]:
                tables = [row.get("tableName") or row.get("table_name") for row in result["data"]]
                return {"success": True, "tables": tables, "catalog": catalog, "schema": schema}
            else:
                return result

        except ValueError as e:
            logger.error(f"Invalid identifier in list_tables: {e}")
            return {"success": False, "message": f"Invalid catalog or schema name: {str(e)}", "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to list Databricks tables: {e}")
            return {"success": False, "message": f"Failed to list tables: {str(e)}", "error": str(e)}

    async def get_table_schema(
        self, table_name: str, catalog: str | None = None, schema: str | None = None
    ) -> dict[str, Any]:
        """Get table schema information.

        Args:
            table_name: Name of the table
            catalog: Catalog name (default: from config)
            schema: Schema name (default: from config)

        Returns:
            Dict with schema information
        """
        try:
            catalog = catalog or self.catalog
            schema = schema or self.schema

            # SECURITY: Validate and sanitize identifiers to prevent SQL injection
            safe_catalog = _sanitize_identifier(catalog)
            safe_schema = _sanitize_identifier(schema)
            safe_table = _sanitize_identifier(table_name)

            query = f"DESCRIBE TABLE {safe_catalog}.{safe_schema}.{safe_table}"
            result = await self.execute_query(query)

            if result["success"]:
                return {"success": True, "schema": result["data"], "table": f"{catalog}.{schema}.{table_name}"}
            else:
                return result

        except ValueError as e:
            logger.error(f"Invalid identifier in get_table_schema: {e}")
            return {"success": False, "message": f"Invalid identifier: {str(e)}", "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return {"success": False, "message": f"Failed to get table schema: {str(e)}", "error": str(e)}

    async def sync(self, incremental: bool = True) -> dict[str, Any]:
        """Sync data from Databricks (not typically used for analysis).

        Args:
            incremental: Whether to do incremental sync

        Returns:
            Dict with sync results
        """
        # For analysis purposes, we don't typically sync Databricks data
        # Instead, we query on-demand
        return {
            "success": True,
            "message": "Databricks connector is query-based, no sync needed",
            "documents_processed": 0,
            "documents_added": 0,
            "documents_updated": 0,
            "documents_failed": 0,
        }

    def get_oauth_url(self) -> str | None:
        """Get OAuth URL (Databricks uses token auth, not OAuth)."""
        return None

    async def handle_oauth_callback(self, code: str) -> dict[str, Any]:
        """Handle OAuth callback (not applicable for Databricks)."""
        return {"success": False, "message": "Databricks uses token authentication, not OAuth"}

    async def connect(self) -> bool:
        """Establish connection to Databricks."""
        result = await self.test_connection()
        return result.get("success", False)

    async def disconnect(self) -> None:
        """Close connection to Databricks."""
        # No persistent connection to close
        pass

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch documents from Databricks (not implemented - query-based connector)."""
        return []

    async def get_document_count(self) -> int:
        """Get total number of documents (not implemented - query-based connector)."""
        return 0

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return ["host", "token", "http_path"]
