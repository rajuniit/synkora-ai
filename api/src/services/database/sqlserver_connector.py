"""SQL Server connector using aioodbc — native asyncio ODBC, no run_in_executor."""

import logging
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class SQLServerConnector:
    """
    Native async SQL Server connector backed by aioodbc.

    aioodbc wraps pyodbc with asyncio, providing truly non-blocking database
    access via an async connection pool.  Requires the Microsoft ODBC Driver
    for SQL Server (msodbcsql17 or msodbcsql18) installed on the host.

    Connection parameters drawn from DatabaseConnection:
        - host                                      SQL Server hostname
        - port                                      default 1433
        - database_name                             target database
        - username                                  SQL Server login
        - password_encrypted                        Fernet-encrypted password
        - connection_params.driver                  ODBC driver name
                                                    (default "ODBC Driver 18 for SQL Server")
        - connection_params.trust_server_certificate  "yes" | "no" (default "yes")
        - connection_params.pool_maxsize            max pool connections (default 10)
    """

    def __init__(self, database_connection: DatabaseConnection) -> None:
        self.database_connection = database_connection
        self._pool = None  # aioodbc.Pool

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_dsn(self, password: str) -> str:
        """Build an ODBC connection string from the DatabaseConnection model."""
        conn_params = self.database_connection.connection_params or {}
        driver = conn_params.get("driver", "ODBC Driver 18 for SQL Server")
        server = self.database_connection.host or "localhost"
        port = int(self.database_connection.port or 1433)
        database = self.database_connection.database_name or ""
        username = self.database_connection.username or ""
        trust_cert = conn_params.get("trust_server_certificate", "yes")

        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate={trust_cert};"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        try:
            import aioodbc  # noqa: PLC0415
        except ImportError:
            logger.error(
                "aioodbc is not installed. "
                "Add 'aioodbc' and 'pyodbc' to dependencies, "
                "and install the Microsoft ODBC Driver for SQL Server on the host."
            )
            return False

        try:
            password = decrypt_value(self.database_connection.password_encrypted)
            dsn = self._build_dsn(password)
            conn_params = self.database_connection.connection_params or {}
            maxsize = int(conn_params.get("pool_maxsize", 10))

            self._pool = await aioodbc.create_pool(
                dsn=dsn,
                minsize=1,
                maxsize=maxsize,
                autocommit=True,
            )

            logger.info(
                "Connected to SQL Server: %s:%s/%s",
                self.database_connection.host,
                self.database_connection.port,
                self.database_connection.database_name,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to SQL Server: %s", e)
            return False

    async def disconnect(self) -> None:
        if self._pool is not None:
            try:
                self._pool.close()
                await self._pool.wait_closed()
                logger.info("Disconnected from SQL Server")
            except Exception as e:
                logger.warning("Error closing SQL Server pool: %s", e)
            finally:
                self._pool = None

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(self, query: str, params: tuple | None = None) -> dict[str, Any]:
        """
        Execute a SQL query and return all rows.

        Uses ``?`` as the ODBC parameter placeholder (same as pyodbc/DB-API 2.0).

        Args:
            query:  SQL query string.
            params: Optional tuple of bind parameters.

        Returns:
            Standard connector result dict.
        """
        if self._pool is None:
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": "Not connected. Call connect() first.",
            }

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)

                    rows_raw = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = [dict(zip(columns, row, strict=False)) for row in rows_raw]

                    return {
                        "success": True,
                        "rows": rows,
                        "row_count": len(rows),
                        "columns": columns,
                    }

        except Exception as e:
            logger.error("SQL Server query failed: %s", e)
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        connected = await self.connect()
        if not connected:
            return {
                "success": False,
                "message": "Failed to establish SQL Server connection",
                "details": {},
            }

        try:
            result = await self.execute_query(
                "SELECT @@VERSION AS version, DB_NAME() AS database_name, @@SERVERNAME AS server_name"
            )
            if not result.get("success"):
                return {
                    "success": False,
                    "message": f"Test query failed: {result.get('error')}",
                    "details": {},
                }

            row = result["rows"][0] if result["rows"] else {}
            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": row.get("version", "unknown"),
                    "database_name": row.get("database_name", self.database_connection.database_name),
                    "server_name": row.get("server_name", "unknown"),
                    "host": self.database_connection.host,
                    "port": self.database_connection.port,
                },
            }

        except Exception as e:
            logger.error("SQL Server connection test failed: %s", e)
            return {"success": False, "message": f"Connection test failed: {e}", "details": {}}
        finally:
            await self.disconnect()

    async def get_tables(self) -> list[str]:
        result = await self.execute_query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        )
        if not result.get("success"):
            logger.error("Failed to list SQL Server tables: %s", result.get("error"))
            return []
        return [row.get("TABLE_NAME", "") for row in result.get("rows", []) if row.get("TABLE_NAME")]

    async def get_schema(self) -> dict[str, Any]:
        try:
            tables = await self.get_tables()
            table_info = []
            for table in tables[:20]:
                cols = await self.execute_query(
                    "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
                    "FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME = ? "
                    "ORDER BY ORDINAL_POSITION",
                    (table,),
                )
                table_info.append(
                    {
                        "name": table,
                        "columns": cols.get("rows", []) if cols.get("success") else [],
                    }
                )
            return {"success": True, "tables": table_info}
        except Exception as e:
            logger.error("Failed to get SQL Server schema: %s", e)
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        result = await self.execute_query(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, "
            "CHARACTER_MAXIMUM_LENGTH "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? "
            "ORDER BY ORDINAL_POSITION",
            (table_name,),
        )
        return {
            "success": result.get("success", False),
            "table_name": table_name,
            "columns": result.get("rows", []),
            **({"error": result["error"]} if not result.get("success") and "error" in result else {}),
        }
