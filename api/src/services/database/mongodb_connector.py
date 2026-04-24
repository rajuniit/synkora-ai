"""MongoDB connector using motor (async MongoDB driver)."""

import logging
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class MongoDBConnector:
    """
    Async MongoDB connector backed by motor.AsyncIOMotorClient.

    Exposes a query interface compatible with the rest of the database layer
    so agents can use it through the same tool interface.
    """

    def __init__(self, database_connection: DatabaseConnection, timeout_ms: int = 30_000):
        self.database_connection = database_connection
        self.timeout_ms = timeout_ms
        self._client = None
        self._db = None

    async def connect(self) -> bool:
        try:
            import motor.motor_asyncio as motor  # noqa: PLC0415

            password = (
                decrypt_value(self.database_connection.password_encrypted)
                if self.database_connection.password_encrypted
                else None
            )

            host = self.database_connection.host or "localhost"
            port = int(self.database_connection.port or 27017)

            if password and self.database_connection.username:
                uri = (
                    f"mongodb://{self.database_connection.username}:{password}"
                    f"@{host}:{port}/{self.database_connection.database_name}"
                )
            else:
                uri = f"mongodb://{host}:{port}"

            self._client = motor.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=self.timeout_ms)
            self._db = self._client[self.database_connection.database_name]

            # Verify connectivity (ping)
            await self._client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {host}:{port}/{self.database_connection.database_name}")
            return True

        except ImportError:
            logger.error("motor is not installed. Add 'motor' to dependencies.")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    async def execute_query(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        """
        Execute a MongoDB query.

        *query* must be a JSON string with the following structure:
        {
            "collection": "my_collection",
            "filter": {},          // optional — MQL filter document
            "projection": {},      // optional — fields to include/exclude
            "limit": 100           // optional — defaults to 100
        }
        """
        if not self._db:
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": "Not connected"}

        try:
            import json

            try:
                q = json.loads(query)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "rows": [],
                    "row_count": 0,
                    "columns": [],
                    "error": "MongoDB query must be a JSON string. See tool description for format.",
                }

            collection_name = q.get("collection")
            if not collection_name:
                return {
                    "success": False,
                    "rows": [],
                    "row_count": 0,
                    "columns": [],
                    "error": "Missing 'collection' key in query",
                }

            collection = self._db[collection_name]
            filt = q.get("filter", {})
            projection = q.get("projection", None)
            limit = min(int(q.get("limit", 100)), 10000)

            cursor = collection.find(filt, projection).limit(limit)
            rows = await cursor.to_list(length=limit)

            # Convert ObjectId to str
            clean_rows = []
            for row in rows:
                clean_row = {}
                for k, v in row.items():
                    clean_row[k] = str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v
                clean_rows.append(clean_row)

            columns = list(clean_rows[0].keys()) if clean_rows else []
            return {"success": True, "rows": clean_rows, "row_count": len(clean_rows), "columns": columns}

        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")
            return {"success": False, "rows": [], "row_count": 0, "columns": [], "error": str(e)}

    async def test_connection(self) -> dict[str, Any]:
        connected = await self.connect()
        if not connected:
            return {"success": False, "message": "Failed to connect", "details": {}}

        try:
            info = await self._client.server_info()
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": info.get("version", "unknown"),
                    "database": self.database_connection.database_name,
                    "host": self.database_connection.host,
                    "port": self.database_connection.port,
                },
            }
        except Exception as e:
            await self.disconnect()
            return {"success": False, "message": f"Connection test failed: {e}", "details": {}}

    async def get_tables(self) -> list[str]:
        """Return collection names (MongoDB equivalent of tables)."""
        if not self._db:
            return []
        try:
            return await self._db.list_collection_names()
        except Exception:
            return []

    async def get_schema(self) -> dict[str, Any]:
        """Sample each collection to infer a rough schema."""
        collections = await self.get_tables()
        schema_info = []
        for coll_name in collections[:20]:
            try:
                coll = self._db[coll_name]
                sample = await coll.find_one()
                columns = list(sample.keys()) if sample else []
                schema_info.append({"name": coll_name, "columns": [{"name": c} for c in columns]})
            except Exception:
                schema_info.append({"name": coll_name, "columns": []})
        return {"success": True, "tables": schema_info}
