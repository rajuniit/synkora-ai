"""
DuckDB database connector — in-process analytics engine.

DuckDB is unique among the connectors in this package:

- **No server required** — the engine runs inside the Python process.
- **In-memory or file-based** — pass ``:memory:`` (default) for ephemeral
  analysis or an absolute path to a ``.duckdb`` file for persistence.
- **Direct file querying** — DuckDB can query CSV, Parquet, JSON, and Arrow
  files without first importing them: ``SELECT * FROM read_csv_auto('path')``.
- **S3 / HTTP access** — with the ``httpfs`` extension loaded, DuckDB reads
  files from ``s3://``, ``https://``, and other remote URLs.
- **PostgreSQL federation** — the ``postgres_scanner`` extension lets DuckDB
  query a live PostgreSQL database as if it were a local table.

Because DuckDB's Python API is synchronous, every blocking call is dispatched
to a thread-pool executor so the asyncio event loop is never blocked.
"""

import asyncio
import logging
import re
from typing import Any

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)

# Safe identifier: letter or underscore, then alphanumeric / underscore
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


def _validate_identifier(identifier: str) -> bool:
    """Return True if *identifier* is safe to interpolate into a SQL string."""
    if not identifier:
        return False
    if not VALID_IDENTIFIER_PATTERN.match(identifier):
        logger.warning("Invalid DuckDB identifier rejected: %s", identifier)
        return False
    if identifier.lower() in DANGEROUS_KEYWORDS:
        logger.warning("Dangerous keyword rejected as identifier: %s", identifier)
        return False
    return True


class DuckDBConnector:
    """
    Async-compatible DuckDB connector for in-process analytics.

    All DuckDB operations run in a ``ThreadPoolExecutor`` via
    ``run_in_executor`` so they do not block the asyncio event loop.

    Connection parameters (from ``DatabaseConnection`` model):
        - ``database_path`` — path to ``.duckdb`` file or ``:memory:``
          (default ``":memory:"``).
        - ``connection_params.extensions`` — list of DuckDB extension names to
          install and load, e.g. ``["httpfs", "postgres_scanner"]``.
        - ``connection_params.s3_region`` — AWS region (default
          ``"us-east-1"``).
        - ``connection_params.s3_access_key_id`` — AWS access key (optional).
        - ``connection_params.s3_secret_access_key`` — AWS secret key
          (optional; may also be stored encrypted in
          ``password_encrypted``).

    The interface mirrors ``PostgreSQLConnector`` and ``MySQLConnector``.
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
            timeout: Reserved for future use (DuckDB does not yet expose a
                     per-query timeout at the Python API level).
        """
        self.database_connection = database_connection
        self.timeout = timeout
        self._conn = None  # duckdb.DuckDBPyConnection

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_sync(self, fn, *args):
        """Run a synchronous callable in the default thread-pool executor."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, fn, *args)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Open (or create) a DuckDB database and load requested extensions.

        Extensions listed in ``connection_params.extensions`` are installed
        (if not already present) and then loaded.  If S3 credentials are
        provided, the ``SET`` statements are executed immediately so that
        subsequent queries can access ``s3://`` URLs.

        Returns:
            True on success, False on failure.
        """
        try:
            import duckdb  # noqa: PLC0415  (deferred — optional dep)
        except ImportError:
            logger.error("duckdb is not installed. Add 'duckdb' to dependencies.")
            return False

        try:
            conn_params = self.database_connection.connection_params or {}
            database_path: str = self.database_connection.database_path or ":memory:"
            extensions: list[str] = conn_params.get("extensions", [])

            # Open the connection in the executor
            def _open() -> Any:
                return duckdb.connect(database_path)

            conn = await self._run_sync(_open)

            # Install / load extensions
            for ext in extensions:
                # Sanitise extension name before embedding in SQL
                safe_ext = re.sub(r"[^a-zA-Z0-9_]", "", ext)
                if safe_ext != ext:
                    logger.warning("Extension name sanitised '%s' -> '%s'", ext, safe_ext)

                def _load_ext(c=conn, e=safe_ext):
                    c.execute(f"INSTALL '{e}'")
                    c.execute(f"LOAD '{e}'")

                await self._run_sync(_load_ext)
                logger.debug("Loaded DuckDB extension: %s", safe_ext)

            # Configure S3 credentials if provided
            s3_region: str = conn_params.get("s3_region", "us-east-1")
            s3_access_key: str | None = conn_params.get("s3_access_key_id")
            # Secret may come from connection_params or the encrypted password field
            s3_secret: str | None = conn_params.get("s3_secret_access_key")
            if not s3_secret and self.database_connection.password_encrypted:
                try:
                    s3_secret = decrypt_value(self.database_connection.password_encrypted)
                except Exception:
                    s3_secret = None

            if s3_access_key and s3_secret:
                # Validate region against an allowlist; escape credentials to
                # prevent SQL injection via DuckDB's string-based SET commands.
                _VALID_S3_REGIONS = {
                    "af-south-1",
                    "ap-east-1",
                    "ap-northeast-1",
                    "ap-northeast-2",
                    "ap-northeast-3",
                    "ap-south-1",
                    "ap-south-2",
                    "ap-southeast-1",
                    "ap-southeast-2",
                    "ap-southeast-3",
                    "ap-southeast-4",
                    "ca-central-1",
                    "ca-west-1",
                    "eu-central-1",
                    "eu-central-2",
                    "eu-north-1",
                    "eu-south-1",
                    "eu-south-2",
                    "eu-west-1",
                    "eu-west-2",
                    "eu-west-3",
                    "il-central-1",
                    "me-central-1",
                    "me-south-1",
                    "sa-east-1",
                    "us-east-1",
                    "us-east-2",
                    "us-gov-east-1",
                    "us-gov-west-1",
                    "us-west-1",
                    "us-west-2",
                }
                if s3_region not in _VALID_S3_REGIONS:
                    raise ValueError(f"Invalid S3 region: {s3_region!r}")

                def _esc(v: str) -> str:
                    """Escape single quotes for DuckDB SET string literals."""
                    return v.replace("'", "''")

                def _set_s3(c=conn, region=s3_region, key=s3_access_key, secret=s3_secret):
                    c.execute(f"SET s3_region='{_esc(region)}'")
                    c.execute(f"SET s3_access_key_id='{_esc(key)}'")
                    c.execute(f"SET s3_secret_access_key='{_esc(secret)}'")

                await self._run_sync(_set_s3)
                logger.debug("S3 credentials configured for DuckDB (region=%s)", s3_region)

            self._conn = conn
            logger.info("DuckDB opened: %s", database_path)
            return True

        except Exception as e:
            logger.error("Failed to open DuckDB: %s", e)
            return False

    async def disconnect(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            try:
                await self._run_sync(self._conn.close)
            except Exception as e:
                logger.warning("Error while closing DuckDB connection: %s", e)
            finally:
                self._conn = None
                logger.info("DuckDB connection closed")

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(self, query: str, params: list[Any] | None = None) -> dict[str, Any]:
        """
        Execute a SQL query (or DuckDB special form) and return results.

        DuckDB supports standard SQL as well as special functions like
        ``read_csv_auto()``, ``read_parquet()``, and ``read_json_auto()``.
        Results are fetched as a pandas DataFrame, then converted to a list of
        plain Python dicts so callers receive a JSON-serialisable structure.

        Args:
            query:  SQL string.  Positional parameters use ``?`` placeholders.
            params: Optional list of parameter values bound to ``?`` placeholders.

        Returns:
            ``{"success": bool, "rows": list[dict], "row_count": int,
               "columns": list[str], "error": str}``
        """
        if self._conn is None:
            return {
                "success": False,
                "rows": [],
                "row_count": 0,
                "columns": [],
                "error": "Not connected. Call connect() first.",
            }

        try:

            def _execute(c=self._conn, q=query, p=params):
                if p:
                    rel = c.execute(q, p)
                else:
                    rel = c.execute(q)
                df = rel.fetchdf()
                return df

            df = await self._run_sync(_execute)

            columns: list[str] = list(df.columns)
            rows: list[dict] = df.to_dict(orient="records")

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "columns": columns,
            }

        except Exception as e:
            logger.error("DuckDB query failed: %s", e)
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
        Verify the DuckDB connection is functional.

        Runs ``SELECT 42 AS answer`` and reports the database path plus any
        extensions that were loaded.

        Returns:
            ``{"success": bool, "message": str, "details": dict}``
        """
        connected = await self.connect()
        if not connected:
            return {"success": False, "message": "Failed to open DuckDB", "details": {}}

        try:
            result = await self.execute_query("SELECT 42 AS answer")
            if not result["success"]:
                return {"success": False, "message": "Connected but test query failed", "details": {}}

            conn_params = self.database_connection.connection_params or {}
            database_path = self.database_connection.database_path or ":memory:"
            extensions = conn_params.get("extensions", [])

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "answer": result["rows"][0].get("answer") if result["rows"] else None,
                    "database_path": database_path,
                    "extensions_loaded": extensions,
                },
            }

        except Exception as e:
            logger.error("DuckDB connection test failed: %s", e)
            return {"success": False, "message": f"Connection test failed: {e}", "details": {}}

        finally:
            await self.disconnect()

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    async def get_tables(self) -> list[str]:
        """
        Return the names of all tables currently in the DuckDB database.

        Returns:
            List of table name strings, empty list on error.
        """
        result = await self.execute_query("SHOW TABLES")
        if not result["success"]:
            return []
        return [list(row.values())[0] for row in result["rows"] if row]

    async def get_schema(self) -> dict[str, Any]:
        """
        Return schema information for up to 20 tables.

        For each table, ``DESCRIBE {table}`` is called to collect column
        names and types.

        Returns:
            ``{"success": bool, "tables": [{"name": str, "columns": [{"name": str, "type": str}]}],
               "error": str}``
        """
        try:
            tables = await self.get_tables()
            table_info = []

            for table in tables[:20]:
                if not _validate_identifier(table):
                    logger.warning("Skipping table with unsafe name during schema fetch: %s", table)
                    continue

                describe_result = await self.execute_query(f'DESCRIBE "{table}"')
                if describe_result["success"]:
                    columns = [
                        {
                            "name": row.get("column_name", row.get("Field", "")),
                            "type": row.get("column_type", row.get("Type", "")),
                        }
                        for row in describe_result["rows"]
                    ]
                else:
                    columns = []

                table_info.append({"name": table, "columns": columns})

            return {"success": True, "tables": table_info}

        except Exception as e:
            logger.error("Failed to get DuckDB schema: %s", e)
            return {"success": False, "tables": [], "error": str(e)}

    async def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Return column details for a specific table via ``DESCRIBE``.

        Args:
            table_name: Name of the table.  Must match
                        ``[A-Za-z_][A-Za-z0-9_]*``.

        Returns:
            ``{"success": bool, "table_name": str, "columns": [{"name": str, "type": str}],
               "error": str}``
        """
        if not _validate_identifier(table_name):
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": f"Invalid or unsafe table name: '{table_name}'",
            }

        result = await self.execute_query(f'DESCRIBE "{table_name}"')
        if not result["success"]:
            return {
                "success": False,
                "table_name": table_name,
                "columns": [],
                "error": result.get("error", "Unknown error"),
            }

        columns = [
            {
                "name": row.get("column_name", row.get("Field", "")),
                "type": row.get("column_type", row.get("Type", "")),
            }
            for row in result["rows"]
        ]

        return {
            "success": True,
            "table_name": table_name,
            "columns": columns,
        }
