"""MySQL database connector using aiomysql."""

import logging
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class MySQLConnector:
    """
    Async MySQL connector backed by aiomysql connection pool.

    Mirrors the interface of PostgreSQLConnector so existing callers
    can treat it interchangeably.
    """

    def __init__(
        self,
        database_connection: DatabaseConnection,
        pool_size: int = 10,
        timeout: float = 30.0,
    ):
        self.database_connection = database_connection
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = None

    async def connect(self) -> bool:
        try:
            import aiomysql  # noqa: PLC0415  (deferred import — optional dep)

            password = decrypt_value(self.database_connection.password_encrypted)

            self._pool = await aiomysql.create_pool(
                host=self.database_connection.host,
                port=int(self.database_connection.port or 3306),
                db=self.database_connection.database_name,
                user=self.database_connection.username,
                password=password,
                maxsize=self.pool_size,
                connect_timeout=self.timeout,
                autocommit=True,
            )
            logger.info(
                f"Connected to MySQL: {self.database_connection.host}:{self.database_connection.port}"
                f"/{self.database_connection.database_name}"
            )
            return True

        except ImportError:
            logger.error("aiomysql is not installed. Add 'aiomysql' to dependencies.")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False

    async def disconnect(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def execute_query(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        if not self._pool:
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": "Not connected"}

        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:  # type: ignore[name-defined]
                    await cur.execute(query, params or ())
                    rows = await cur.fetchall()
                    columns = [d[0] for d in cur.description] if cur.description else []
                    return {"success": True, "rows": [dict(r) for r in rows], "row_count": len(rows), "columns": columns}
        except Exception as e:
            logger.error(f"MySQL query failed: {e}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

    async def test_connection(self) -> dict[str, Any]:
        connected = await self.connect()
        if not connected:
            return {"success": False, "message": "Failed to connect", "details": {}}

        result = await self.execute_query("SELECT VERSION() AS version")
        await self.disconnect()

        if result.get("success") and result["rows"]:
            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": result["rows"][0].get("version", "unknown"),
                    "database": self.database_connection.database_name,
                    "host": self.database_connection.host,
                    "port": self.database_connection.port,
                },
            }
        return {"success": False, "message": "Connection test failed", "details": {}}

    async def get_tables(self) -> list[str]:
        result = await self.execute_query("SHOW TABLES")
        if not result.get("success"):
            return []
        return [list(row.values())[0] for row in result.get("rows", []) if row]

    async def get_schema(self) -> dict[str, Any]:
        tables = await self.get_tables()
        table_info = []
        for table in tables[:20]:
            cols_result = await self.execute_query(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION",
                [table],
            )
            columns = cols_result.get("rows", []) if cols_result.get("success") else []
            table_info.append({"name": table, "columns": columns})
        return {"success": True, "tables": table_info}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        cols_result = await self.execute_query(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION",
            [table_name],
        )
        return {
            "success": cols_result.get("success", False),
            "table_name": table_name,
            "columns": cols_result.get("rows", []),
        }
