"""PostgreSQL database connector with connection pooling and query execution."""

import logging
import re
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from asyncpg.pool import Pool

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)

# Regex pattern for valid PostgreSQL identifiers
# Only allows alphanumeric characters and underscores, must start with letter or underscore
VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class PostgreSQLConnector:
    """
    PostgreSQL connector with connection pooling and safe query execution.

    Provides connection management, query execution, and schema introspection
    for PostgreSQL databases.
    """

    def __init__(
        self,
        database_connection: DatabaseConnection,
        pool_size: int = 10,
        max_queries: int = 50000,
        timeout: float = 30.0,
    ):
        """
        Initialize PostgreSQL connector.

        Args:
            database_connection: DatabaseConnection model instance
            pool_size: Maximum number of connections in the pool
            max_queries: Maximum number of queries per connection
            timeout: Query timeout in seconds
        """
        self.database_connection = database_connection
        self.pool_size = pool_size
        self.max_queries = max_queries
        self.timeout = timeout
        self.pool: Pool | None = None
        self._valid_tables_cache: set[str] | None = None

    def _validate_identifier(self, identifier: str) -> bool:
        """
        Validate that an identifier (table/column name) is safe.

        Args:
            identifier: The identifier to validate

        Returns:
            True if identifier is valid, False otherwise
        """
        if not identifier:
            return False

        # Check against regex pattern for valid PostgreSQL identifiers
        if not VALID_IDENTIFIER_PATTERN.match(identifier):
            logger.warning(f"Invalid identifier rejected: {identifier}")
            return False

        # Additional check: reject if it looks like SQL injection
        dangerous_keywords = [
            "select",
            "insert",
            "update",
            "delete",
            "drop",
            "truncate",
            "create",
            "alter",
            "grant",
            "revoke",
            "union",
            "exec",
            "execute",
        ]
        if identifier.lower() in dangerous_keywords:
            logger.warning(f"Dangerous keyword rejected as identifier: {identifier}")
            return False

        return True

    def _quote_identifier(self, identifier: str) -> str:
        """
        Safely quote a PostgreSQL identifier (table/column name).

        Args:
            identifier: The identifier to quote

        Returns:
            Safely quoted identifier

        Raises:
            ValueError: If identifier is invalid
        """
        if not self._validate_identifier(identifier):
            raise ValueError(f"Invalid identifier: {identifier}")

        # Double any existing double quotes and wrap in double quotes
        # This is the standard PostgreSQL way to quote identifiers
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    async def _get_valid_tables(self) -> set[str]:
        """
        Get and cache the set of valid table names from the database schema.

        Returns:
            Set of valid table names
        """
        if self._valid_tables_cache is not None:
            return self._valid_tables_cache

        tables = await self.get_tables()
        self._valid_tables_cache = set(tables)
        return self._valid_tables_cache

    async def _validate_table_exists(self, table_name: str) -> bool:
        """
        Validate that a table exists in the database schema.

        Args:
            table_name: Name of the table to validate

        Returns:
            True if table exists, False otherwise
        """
        if not self._validate_identifier(table_name):
            return False

        valid_tables = await self._get_valid_tables()
        if table_name not in valid_tables:
            logger.warning(f"Table name not found in schema: {table_name}")
            return False

        return True

    def clear_table_cache(self) -> None:
        """Clear the cached table list (call after schema changes)."""
        self._valid_tables_cache = None

    async def connect(self) -> bool:
        """
        Establish connection pool to PostgreSQL.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Decrypt password
            password = decrypt_value(self.database_connection.password_encrypted)

            # Get connection parameters
            conn_params = self.database_connection.connection_params or {}

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.database_connection.host,
                port=self.database_connection.port,
                database=self.database_connection.database_name,
                user=self.database_connection.username,
                password=password,
                min_size=1,
                max_size=self.pool_size,
                max_queries=self.max_queries,
                command_timeout=self.timeout,
                **conn_params,
            )

            logger.info(
                f"Connected to PostgreSQL: {self.database_connection.host}:"
                f"{self.database_connection.port}/{self.database_connection.database_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Disconnected from PostgreSQL")

    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool.

        Yields:
            Database connection
        """
        if not self.pool:
            raise RuntimeError("Connection pool not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            yield conn

    async def execute_query(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dictionary with query results:
                {
                    "success": bool,
                    "rows": List[Dict],
                    "row_count": int,
                    "columns": List[str],
                    "error": str (if failed)
                }
        """
        try:
            async with self.get_connection() as conn:
                # Execute query
                if params:
                    result = await conn.fetch(query, *params)
                else:
                    result = await conn.fetch(query)

                # Convert to list of dictionaries
                rows = [dict(row) for row in result]
                columns = list(result[0].keys()) if result else []

                return {"success": True, "rows": rows, "row_count": len(rows), "columns": columns}

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

    async def execute_count(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        """
        Execute a COUNT query.

        Args:
            query: SQL COUNT query
            params: Query parameters

        Returns:
            Dictionary with count result
        """
        try:
            async with self.get_connection() as conn:
                if params:
                    count = await conn.fetchval(query, *params)
                else:
                    count = await conn.fetchval(query)

                return {"success": True, "count": count}

        except Exception as e:
            logger.error(f"Count query failed: {str(e)}")
            return {"success": False, "count": 0, "error": str(e)}

    async def test_connection(self) -> dict[str, Any]:
        """
        Test the connection to PostgreSQL.

        Returns:
            Dictionary with test results
        """
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to establish connection", "details": {}}

            # Execute simple query to get version
            async with self.get_connection() as conn:
                version_result = await conn.fetchrow("SELECT version()")
                version = version_result["version"] if version_result else "Unknown"

                # Get database size
                size_result = await conn.fetchrow("SELECT pg_database_size(current_database()) as size")
                db_size = size_result["size"] if size_result else 0

            await self.disconnect()

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": version,
                    "database": self.database_connection.database_name,
                    "host": self.database_connection.host,
                    "port": self.database_connection.port,
                    "database_size_bytes": db_size,
                },
            }

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}", "details": {}}

    async def get_tables(self) -> list[str]:
        """
        Get list of table names in the database.

        Returns:
            List of table names
        """
        try:
            async with self.get_connection() as conn:
                tables_query = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                tables_result = await conn.fetch(tables_query)
                return [row["table_name"] for row in tables_result]

        except Exception as e:
            logger.error(f"Failed to get tables: {str(e)}")
            return []

    async def get_schema(self) -> dict[str, Any]:
        """
        Get database schema information.

        Returns:
            Dictionary with schema information:
                {
                    "success": bool,
                    "tables": List[Dict],
                    "error": str (if failed)
                }
        """
        try:
            async with self.get_connection() as conn:
                # Get all tables
                tables_query = """
                    SELECT
                        table_name,
                        table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                tables_result = await conn.fetch(tables_query)

                tables = []
                for table_row in tables_result:
                    table_name = table_row["table_name"]

                    # Get columns for this table
                    columns_query = """
                        SELECT
                            column_name,
                            data_type,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = $1
                        ORDER BY ordinal_position
                    """
                    columns_result = await conn.fetch(columns_query, table_name)

                    columns = [
                        {
                            "name": col["column_name"],
                            "type": col["data_type"],
                            "nullable": col["is_nullable"] == "YES",
                            "default": col["column_default"],
                        }
                        for col in columns_result
                    ]

                    tables.append({"name": table_name, "type": table_row["table_type"], "columns": columns})

                return {"success": True, "tables": tables}

        except Exception as e:
            logger.error(f"Failed to get schema: {str(e)}")
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table information
        """
        try:
            # SECURITY: Validate table name exists in schema before using it
            if not await self._validate_table_exists(table_name):
                return {"success": False, "error": f"Table '{table_name}' not found or invalid"}

            async with self.get_connection() as conn:
                # Get columns
                columns_query = """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = $1
                    ORDER BY ordinal_position
                """
                columns = await conn.fetch(columns_query, table_name)

                # Get primary keys - use schema lookup instead of regclass cast
                pk_query = """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                    JOIN pg_class c ON c.oid = i.indrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = $1
                    AND n.nspname = 'public'
                    AND i.indisprimary
                """
                pks = await conn.fetch(pk_query, table_name)
                primary_keys = [pk["attname"] for pk in pks]

                # Get foreign keys
                fk_query = """
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = $1
                """
                fks = await conn.fetch(fk_query, table_name)

                # SECURITY: Get row count using safe quoted identifier
                safe_table_name = self._quote_identifier(table_name)
                count_query = f"SELECT COUNT(*) FROM {safe_table_name}"
                row_count = await conn.fetchval(count_query)

                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": [dict(col) for col in columns],
                    "primary_keys": primary_keys,
                    "foreign_keys": [dict(fk) for fk in fks],
                    "row_count": row_count,
                }

        except Exception as e:
            logger.error(f"Failed to get table info: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_sample_data(self, table_name: str, limit: int = 10) -> dict[str, Any]:
        """
        Get sample data from a table.

        Args:
            table_name: Name of the table
            limit: Number of rows to fetch (max 1000)

        Returns:
            Dictionary with sample data
        """
        try:
            # SECURITY: Validate table name exists in schema before using it
            if not await self._validate_table_exists(table_name):
                return {"success": False, "rows": [], "error": f"Table '{table_name}' not found or invalid"}

            # SECURITY: Enforce maximum limit to prevent DoS
            limit = min(limit, 1000)

            # SECURITY: Use safe quoted identifier
            safe_table_name = self._quote_identifier(table_name)
            query = f"SELECT * FROM {safe_table_name} LIMIT $1"
            result = await self.execute_query(query, [limit])
            return result

        except Exception as e:
            logger.error(f"Failed to get sample data: {str(e)}")
            return {"success": False, "rows": [], "error": str(e)}
