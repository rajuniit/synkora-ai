"""ClickHouse database connector using the official clickhouse-connect client."""

import logging
import re
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)

# Only alphanumeric and underscores — no dots, hyphens, or spaces
VALID_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

DANGEROUS_KEYWORDS = frozenset(
    [
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
)


class ClickHouseConnector:
    """
    Async ClickHouse connector backed by clickhouse-connect.

    clickhouse-connect communicates with ClickHouse over HTTP/HTTPS, so no
    separate TCP driver is needed.  The async client is obtained via
    ``clickhouse_connect.get_async_client()``, which is an asyncio-native
    wrapper around the same HTTP session.

    Connection parameters are read from a ``DatabaseConnection`` model:
        - host / port
        - database_name  (defaults to ``default``)
        - username        (defaults to ``default``)
        - password_encrypted — decrypted at connect time
        - connection_params.secure  (bool, default False) — use HTTPS
        - connection_params.verify  (bool, default True)  — verify SSL cert

    The interface mirrors ``PostgreSQLConnector`` and ``MySQLConnector`` so
    callers can treat all connectors interchangeably.
    """

    def __init__(
        self,
        database_connection: DatabaseConnection,
        timeout: float = 30.0,
    ):
        """
        Initialise the connector.

        Args:
            database_connection: DatabaseConnection model instance.
            timeout: Query / connect timeout in seconds.
        """
        self.database_connection = database_connection
        self.timeout = timeout
        self._client = None

    # ------------------------------------------------------------------
    # Identifier safety
    # ------------------------------------------------------------------

    def _validate_identifier(self, identifier: str) -> bool:
        """
        Return True if ``identifier`` is a safe table / column name.

        Rejects empty strings, SQL keywords, and anything containing
        characters outside ``[A-Za-z0-9_]``.
        """
        if not identifier:
            return False
        if not VALID_IDENTIFIER_PATTERN.match(identifier):
            logger.warning("Invalid ClickHouse identifier rejected: %s", identifier)
            return False
        if identifier.lower() in DANGEROUS_KEYWORDS:
            logger.warning("Dangerous keyword rejected as identifier: %s", identifier)
            return False
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Create an async ClickHouse client.

        Returns:
            True on success, False on failure (ImportError or connection error).
        """
        try:
            import clickhouse_connect  # noqa: PLC0415  (deferred — optional dep)
        except ImportError:
            logger.error("clickhouse-connect is not installed. Add 'clickhouse-connect' to dependencies.")
            return False

        try:
            password = ""
            if self.database_connection.password_encrypted:
                password = decrypt_value(self.database_connection.password_encrypted)

            conn_params = self.database_connection.connection_params or {}
            secure: bool = bool(conn_params.get("secure", False))
            verify: bool = bool(conn_params.get("verify", True))

            host = self.database_connection.host or "localhost"
            # Default HTTP port is 8123; HTTPS is 8443
            port = self.database_connection.port or (8443 if secure else 8123)
            database = self.database_connection.database_name or "default"
            username = self.database_connection.username or "default"

            self._client = await clickhouse_connect.get_async_client(
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                secure=secure,
                verify=verify,
                connect_timeout=int(self.timeout),
                query_limit=0,  # no row limit imposed by the client
            )

            logger.info(
                "Connected to ClickHouse: %s:%s/%s",
                host,
                port,
                database,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to ClickHouse: %s", e)
            return False

    async def disconnect(self) -> None:
        """Close the ClickHouse client session."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning("Error while closing ClickHouse client: %s", e)
            finally:
                self._client = None
                logger.info("Disconnected from ClickHouse")

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        """
        Execute a SQL query against ClickHouse.

        Args:
            query: SQL query string.  Use ``{param:Type}`` placeholders if
                   passing *params* (ClickHouse-connect named-param style).
            params: Optional list of positional values.  They are mapped to
                    ``{p0:...}, {p1:...}`` placeholders automatically when
                    the client supports it.  For most ad-hoc use cases pass
                    params=None and embed values in the query string.

        Returns:
            ``{"success": bool, "rows": list[dict], "row_count": int,
               "columns": list[str], "error": str}``
        """
        if self._client is None:
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": "Not connected. Call connect() first.",
            }

        try:
            result = await self._client.query(query, parameters=params)
            column_names: list[str] = list(result.column_names)
            rows = [dict(zip(column_names, row)) for row in result.result_rows]

            return {
                "success": True,
                "rows": rows,
                "row_count": result.row_count,
                "columns": column_names,
            }

        except Exception as e:
            logger.error("ClickHouse query failed: %s", e)
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
        """
        Verify connectivity and return server metadata.

        Connects, runs ``SELECT version()`` and ``SELECT currentDatabase()``,
        then disconnects.

        Returns:
            ``{"success": bool, "message": str, "details": dict}``
        """
        connected = await self.connect()
        if not connected:
            return {"success": False, "message": "Failed to establish connection", "details": {}}

        try:
            version_result = await self.execute_query("SELECT version() AS version")
            db_result = await self.execute_query("SELECT currentDatabase() AS database")

            if not version_result["success"] or not db_result["success"]:
                return {
                    "success": False,
                    "message": "Connected but could not retrieve server info",
                    "details": {},
                }

            version = version_result["rows"][0].get("version", "unknown") if version_result["rows"] else "unknown"
            current_db = db_result["rows"][0].get("database", "unknown") if db_result["rows"] else "unknown"

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": version,
                    "database": current_db,
                    "host": self.database_connection.host or "localhost",
                    "port": self.database_connection.port,
                },
            }

        except Exception as e:
            logger.error("ClickHouse connection test failed: %s", e)
            return {"success": False, "message": f"Connection test failed: {e}", "details": {}}

        finally:
            await self.disconnect()

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    async def get_tables(self) -> list[str]:
        """
        Return a list of table names in the current database.

        Returns:
            List of table name strings, empty list on error.
        """
        database = self.database_connection.database_name or "default"
        result = await self.execute_query(f"SHOW TABLES FROM `{database}`")
        if not result["success"]:
            return []
        return [list(row.values())[0] for row in result["rows"] if row]

    async def get_schema(self) -> dict[str, Any]:
        """
        Return schema information for up to 20 tables in the database.

        For each table, ``DESCRIBE TABLE`` is called to collect column names
        and types.

        Returns:
            ``{"success": bool, "tables": [{"name": str, "columns": [{"name": str, "type": str}]}],
               "error": str}``
        """
        try:
            tables = await self.get_tables()
            table_info = []

            for table in tables[:20]:
                if not self._validate_identifier(table):
                    logger.warning("Skipping table with unsafe name during schema fetch: %s", table)
                    continue

                describe_result = await self.execute_query(f"DESCRIBE TABLE `{table}`")
                if describe_result["success"]:
                    columns = [
                        {"name": row.get("name", ""), "type": row.get("type", "")}
                        for row in describe_result["rows"]
                    ]
                else:
                    columns = []

                table_info.append({"name": table, "columns": columns})

            return {"success": True, "tables": table_info}

        except Exception as e:
            logger.error("Failed to get ClickHouse schema: %s", e)
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Return column details for a specific table via ``DESCRIBE TABLE``.

        Args:
            table_name: Name of the table.  Must match ``[A-Za-z_][A-Za-z0-9_]*``.

        Returns:
            ``{"success": bool, "table_name": str, "columns": [{"name": str, "type": str}],
               "error": str}``
        """
        if not self._validate_identifier(table_name):
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": f"Invalid or unsafe table name: '{table_name}'",
            }

        result = await self.execute_query(f"DESCRIBE TABLE `{table_name}`")
        if not result["success"]:
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": result.get("error", "Unknown error"),
            }

        columns = [
            {"name": row.get("name", ""), "type": row.get("type", "")}
            for row in result["rows"]
        ]

        return {
            "success": True,
            "table_name": table_name,
            "columns": columns,
        }
