"""
DuckDB end-to-end integration tests.

Runs against the live API server at localhost:5001 with real DuckDB engine,
real database records, and real connector caching.

Covers:
  - Connection create / test / delete via REST API
  - In-memory queries through /api/v1/data-analysis/query-database
  - DuckDB-specific SQL (generate_series, VALUES, inline aggregations)
  - File-based DuckDB with persistent data across queries
  - Row-count guard: broad SELECT blocked for tables > 50 K rows
  - Row-count guard: aggregation / LIMIT queries pass through cleanly

Usage:
    pytest tests/integration/test_duckdb_e2e.py -v -s
"""

import asyncio
import os
import tempfile
import uuid
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

BASE_URL = "http://localhost:5001"

# ---------------------------------------------------------------------------
# Auth helpers — one login for the whole test session (avoids rate limiting)
# ---------------------------------------------------------------------------

_TOKEN: str | None = None


def _get_token() -> str:
    global _TOKEN
    if _TOKEN is None:
        r = httpx.post(
            f"{BASE_URL}/console/api/auth/login",
            json={"email": "admin@locahost.com", "password": "Admin123!"},
            timeout=15,
        )
        r.raise_for_status()
        _TOKEN = r.json()["data"]["access_token"]
    return _TOKEN


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _create_connection(token: str, name: str, database_path: str = ":memory:") -> dict:
    """Create a DuckDB database connection and return the JSON response body."""
    r = httpx.post(
        f"{BASE_URL}/api/v1/database-connections",
        json={
            "name": name,
            "type": "DUCKDB",
            "database_path": database_path,
            # DuckDB doesn't need host/port/credentials
        },
        headers=_headers(token),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _delete_connection(token: str, connection_id: str) -> None:
    r = httpx.delete(
        f"{BASE_URL}/api/v1/database-connections/{connection_id}",
        headers=_headers(token),
        timeout=10,
    )
    assert r.status_code in (200, 204)


def _query(token: str, connection_id: str, sql: str, _retries: int = 5) -> dict:
    """Execute a SQL query and return the full response body.

    Retries up to *_retries* times on 429 (rate limit) with a short back-off.
    """
    import time as _time

    for attempt in range(_retries):
        r = httpx.post(
            f"{BASE_URL}/api/v1/data-analysis/query-database",
            json={"connection_id": connection_id, "query": sql},
            headers=_headers(token),
            timeout=30,
        )
        if r.status_code == 429 and attempt < _retries - 1:
            _time.sleep(2 + attempt * 2)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()  # final attempt
    return r.json()


# ---------------------------------------------------------------------------
# DuckDB in-memory connection tests
# ---------------------------------------------------------------------------


class TestDuckDBConnectionLifecycle:
    """Create → test → list → delete via the database-connections REST API."""

    def setup_method(self):
        self.token = _get_token()
        self.created_ids: list[str] = []

    def teardown_method(self):
        for cid in self.created_ids:
            try:
                _delete_connection(self.token, cid)
            except Exception:
                pass

    def test_create_memory_connection(self):
        conn = _create_connection(self.token, f"duckdb-mem-{uuid.uuid4().hex[:6]}")
        self.created_ids.append(conn["id"])
        assert conn["id"]
        assert conn["type"].upper() == "DUCKDB"

    def test_test_connection_succeeds(self):
        conn = _create_connection(self.token, f"duckdb-test-{uuid.uuid4().hex[:6]}")
        self.created_ids.append(conn["id"])

        r = httpx.post(
            f"{BASE_URL}/api/v1/database-connections/{conn['id']}/test",
            headers=_headers(self.token),
            timeout=20,
        )
        r.raise_for_status()
        body = r.json()
        assert body["success"] is True
        assert "Connection successful" in (body.get("message") or "")

    def test_connection_appears_in_list(self):
        name = f"duckdb-list-{uuid.uuid4().hex[:6]}"
        conn = _create_connection(self.token, name)
        self.created_ids.append(conn["id"])

        r = httpx.get(
            f"{BASE_URL}/api/v1/database-connections",
            headers=_headers(self.token),
            timeout=10,
        )
        r.raise_for_status()
        ids = [c["id"] for c in r.json()]
        assert conn["id"] in ids

    def test_delete_connection(self):
        conn = _create_connection(self.token, f"duckdb-del-{uuid.uuid4().hex[:6]}")
        cid = conn["id"]
        _delete_connection(self.token, cid)
        # Fetching it should now 404
        r = httpx.get(
            f"{BASE_URL}/api/v1/database-connections/{cid}",
            headers=_headers(self.token),
            timeout=10,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DuckDB query execution (in-memory, self-contained SQL)
# ---------------------------------------------------------------------------


class TestDuckDBQueryExecution:
    """Run various SQL statements through /api/v1/data-analysis/query-database."""

    def setup_method(self):
        self.token = _get_token()
        conn = _create_connection(self.token, f"duckdb-query-{uuid.uuid4().hex[:6]}")
        self.conn_id = conn["id"]

    def teardown_method(self):
        try:
            _delete_connection(self.token, self.conn_id)
        except Exception:
            pass

    # -- basic arithmetic --------------------------------------------------

    def test_select_literal(self):
        body = _query(self.token, self.conn_id, "SELECT 6 * 7 AS answer")
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        assert rows[0]["answer"] == 42

    # -- inline VALUES (DuckDB supports standard SQL VALUES) ---------------

    def test_inline_values(self):
        body = _query(
            self.token,
            self.conn_id,
            "SELECT * FROM (VALUES (1,'alice'),(2,'bob')) AS t(id,name) ORDER BY id",
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        assert len(rows) == 2
        assert rows[0]["name"] == "alice"
        assert rows[1]["id"] == 2

    # -- DuckDB generate_series (table-valued function) --------------------

    def test_generate_series(self):
        body = _query(
            self.token,
            self.conn_id,
            "SELECT n FROM generate_series(1, 5) AS s(n) ORDER BY n",
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        assert len(rows) == 5
        assert [r["n"] for r in rows] == [1, 2, 3, 4, 5]

    # -- aggregation -------------------------------------------------------

    def test_aggregation_with_group_by(self):
        body = _query(
            self.token,
            self.conn_id,
            """
            SELECT region, SUM(sales) AS total
            FROM (VALUES
                ('east',  100),
                ('west',  200),
                ('east',  150)
            ) AS t(region, sales)
            GROUP BY region
            ORDER BY region
            """,
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        by_region = {r["region"]: r["total"] for r in rows}
        assert by_region["east"] == 250
        assert by_region["west"] == 200

    # -- COUNT and HAVING --------------------------------------------------

    def test_count_having(self):
        body = _query(
            self.token,
            self.conn_id,
            """
            SELECT category, COUNT(*) AS cnt
            FROM (VALUES
                ('A'),('A'),('A'),('B'),('B'),('C')
            ) AS t(category)
            GROUP BY category
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            """,
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        # A=3, B=2 pass; C=1 filtered
        assert len(rows) == 2
        assert rows[0]["category"] == "A"
        assert rows[0]["cnt"] == 3

    # -- date arithmetic (DuckDB extension) --------------------------------

    def test_date_functions(self):
        body = _query(
            self.token,
            self.conn_id,
            """
            SELECT
                DATE '2025-01-15' AS d,
                EXTRACT(MONTH FROM DATE '2025-01-15') AS month_num,
                DATEDIFF('day', DATE '2025-01-01', DATE '2025-01-15') AS days_diff
            """,
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        assert rows[0]["month_num"] == 1
        assert rows[0]["days_diff"] == 14

    # -- window functions --------------------------------------------------

    def test_window_function_rank(self):
        body = _query(
            self.token,
            self.conn_id,
            """
            SELECT name, score,
                   RANK() OVER (ORDER BY score DESC) AS rnk
            FROM (VALUES
                ('alice', 95),
                ('bob',   87),
                ('carol', 95),
                ('dave',  72)
            ) AS t(name, score)
            ORDER BY rnk, name
            """,
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        # alice and carol tied at rank 1, bob rank 3, dave rank 4
        rank1 = [r["name"] for r in rows if r["rnk"] == 1]
        assert set(rank1) == {"alice", "carol"}

    # -- JSON support ------------------------------------------------------

    def test_json_extract(self):
        body = _query(
            self.token,
            self.conn_id,
            """
            SELECT
                json_extract('{"user": {"name": "alice", "age": 30}}', '$.user.name') AS uname,
                json_extract_string('{"score": 99}', '$.score') AS score
            """,
        )
        assert body["success"] is True
        rows = body["data"]["data"]["rows"]
        assert "alice" in str(rows[0]["uname"])


# ---------------------------------------------------------------------------
# DuckDB file-based persistence
# ---------------------------------------------------------------------------


class TestDuckDBFilePersistence:
    """
    Use a file-based DuckDB so that data created in one API call is visible
    in subsequent calls (because the connector cache reuses the same file).
    """

    FILE_PATH = "/tmp/duckdb_integration_test.duckdb"

    def setup_method(self):
        self.token = _get_token()
        # Use a unique file path per test run to avoid cross-test pollution
        self.file_path = f"/tmp/duckdb_int_{uuid.uuid4().hex[:8]}.duckdb"
        conn = _create_connection(self.token, f"duckdb-file-{uuid.uuid4().hex[:6]}", database_path=self.file_path)
        self.conn_id = conn["id"]

    def teardown_method(self):
        try:
            _delete_connection(self.token, self.conn_id)
        except Exception:
            pass
        try:
            os.remove(self.file_path)
        except Exception:
            pass

    def test_create_and_query_table(self):
        # Step 1: create table + insert
        r1 = _query(
            self.token,
            self.conn_id,
            "CREATE TABLE events (id INTEGER, event_type VARCHAR, ts DATE)",
        )
        assert r1["success"] is True

        r2 = _query(
            self.token,
            self.conn_id,
            """
            INSERT INTO events VALUES
                (1, 'login',   '2025-01-01'),
                (2, 'purchase','2025-01-01'),
                (3, 'login',   '2025-01-02'),
                (4, 'logout',  '2025-01-02'),
                (5, 'purchase','2025-01-02')
            """,
        )
        assert r2["success"] is True

        # Step 2: aggregate query — events by type
        r3 = _query(
            self.token,
            self.conn_id,
            "SELECT event_type, COUNT(*) AS cnt FROM events GROUP BY event_type ORDER BY cnt DESC",
        )
        assert r3["success"] is True
        rows = r3["data"]["data"]["rows"]
        by_type = {r["event_type"]: r["cnt"] for r in rows}
        assert by_type["login"] == 2
        assert by_type["purchase"] == 2
        assert by_type["logout"] == 1

    def test_csv_writing_and_reading(self):
        """Create a table, export to CSV via DuckDB COPY, read it back."""
        _query(self.token, self.conn_id, "CREATE TABLE nums (n INTEGER)")
        _query(
            self.token,
            self.conn_id,
            "INSERT INTO nums SELECT * FROM generate_series(1, 10) AS s(n)",
        )

        csv_path = f"/tmp/duckdb_csv_{uuid.uuid4().hex[:6]}.csv"
        _query(self.token, self.conn_id, f"COPY nums TO '{csv_path}' (HEADER, DELIMITER ',')")

        # Read back via read_csv_auto
        r = _query(
            self.token,
            self.conn_id,
            f"SELECT SUM(n) AS total FROM read_csv_auto('{csv_path}')",
        )
        assert r["success"] is True
        rows = r["data"]["data"]["rows"]
        # SUM(1..10) = 55
        assert int(rows[0]["total"]) == 55


# ---------------------------------------------------------------------------
# Row-count guard  (direct internal function test against real DuckDB file)
# ---------------------------------------------------------------------------

# Module-level shared state for the guard test class (set once in setup_class)
_GUARD_CONN_ID: str | None = None
_GUARD_FILE_PATH: str | None = None
_GUARD_TENANT_ID: str | None = None
_GUARD_DB_CONN: Any = None  # MagicMock DatabaseConnection used across all guard tests


def _make_mock_session(db_conn_obj: Any) -> Any:
    """Return an AsyncSession mock whose execute() returns db_conn_obj."""

    async def _execute(*args: Any, **kwargs: Any) -> Any:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=db_conn_obj)
        return mock_result

    mock_session = MagicMock()
    mock_session.execute = _execute
    return mock_session


class TestRowCountGuard:
    """
    Test the row-count guard in internal_query_database.

    Strategy:
      1. In setup_class: create a real DuckDB file with 100 000 rows using
         DuckDBConnector directly (no HTTP, no SQLAlchemy to the live DB).
         Construct a MagicMock DatabaseConnection whose attributes match what
         database_tools.py reads — no DB insert needed.
      2. Each test calls internal_query_database directly with the mock session
         that returns the mock DatabaseConnection.
      3. Verify broad SELECT blocked; GROUP BY / COUNT / LIMIT queries pass.

    This avoids both the HTTP rate-limiter and the conftest.py DB redirect to
    synkora_test (which has no tenant_account_joins table).
    """

    @classmethod
    def setup_class(cls) -> None:
        """
        Create a file-based DuckDB with 100 K rows and a corresponding mock
        DatabaseConnection, entirely without any HTTP or PostgreSQL calls.
        """
        global _GUARD_CONN_ID, _GUARD_FILE_PATH, _GUARD_TENANT_ID, _GUARD_DB_CONN

        conn_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        file_path = f"/tmp/duckdb_guard_{uuid.uuid4().hex[:8]}.duckdb"

        async def _create_duckdb_file() -> None:
            from unittest.mock import MagicMock as _MM

            from src.services.database.duckdb_connector import DuckDBConnector

            seed_conn = _MM()
            seed_conn.database_path = file_path
            seed_conn.connection_params = {}
            seed_conn.password_encrypted = None
            connector = DuckDBConnector(seed_conn)
            await connector.connect()
            await connector.execute_query("CREATE TABLE big_table AS SELECT * FROM generate_series(1, 100000) AS s(n)")
            await connector.execute_query("CREATE TABLE small_table AS SELECT * FROM generate_series(1, 100) AS s(n)")
            await connector.disconnect()

        asyncio.run(_create_duckdb_file())

        # Build a mock DatabaseConnection whose attributes satisfy database_tools.py
        mock_conn = MagicMock()
        mock_conn.id = uuid.UUID(conn_id)
        mock_conn.database_type = "DUCKDB"
        mock_conn.status = "active"
        mock_conn.name = "guard-test"
        mock_conn.database_path = file_path
        mock_conn.connection_params = {}
        mock_conn.password_encrypted = None
        mock_conn.tenant_id = uuid.UUID(tenant_id)

        _GUARD_CONN_ID = conn_id
        _GUARD_FILE_PATH = file_path
        _GUARD_TENANT_ID = tenant_id
        _GUARD_DB_CONN = mock_conn

    @classmethod
    def teardown_class(cls) -> None:
        from src.services.agents.internal_tools.database_tools import _connector_cache

        _connector_cache.pop(_GUARD_CONN_ID, None)
        try:
            os.remove(_GUARD_FILE_PATH)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_broad_select_blocked_for_large_table(self) -> None:
        """SELECT * with no LIMIT/GROUP BY on a 100K-row table must be blocked."""
        from src.services.agents.internal_tools.database_tools import internal_query_database

        result = await internal_query_database(
            connection_id=_GUARD_CONN_ID,
            query="SELECT * FROM big_table",
            tenant_id=_GUARD_TENANT_ID,
            db_session=_make_mock_session(_GUARD_DB_CONN),
        )

        assert result["success"] is False, f"Expected guard to block, got: {result}"
        assert "big_table" in result["error"] or "50,000" in result["error"]
        assert result.get("row_count_estimate", 0) >= 100_000

    @pytest.mark.asyncio
    async def test_aggregation_count_passes_guard(self) -> None:
        """SELECT COUNT(*) on large table must not be blocked."""
        from src.services.agents.internal_tools.database_tools import internal_query_database

        result = await internal_query_database(
            connection_id=_GUARD_CONN_ID,
            query="SELECT COUNT(*) AS total FROM big_table",
            tenant_id=_GUARD_TENANT_ID,
            db_session=_make_mock_session(_GUARD_DB_CONN),
        )

        assert result["success"] is True, f"COUNT query should pass: {result}"
        assert result["data"][0]["total"] == 100_000

    @pytest.mark.asyncio
    async def test_limit_passes_guard(self) -> None:
        """SELECT with LIMIT on large table must not be blocked."""
        from src.services.agents.internal_tools.database_tools import internal_query_database

        result = await internal_query_database(
            connection_id=_GUARD_CONN_ID,
            query="SELECT n FROM big_table ORDER BY n LIMIT 10",
            tenant_id=_GUARD_TENANT_ID,
            db_session=_make_mock_session(_GUARD_DB_CONN),
        )

        assert result["success"] is True, f"LIMIT query should pass: {result}"
        assert result["row_count"] == 10
        assert result["data"][0]["n"] == 1

    @pytest.mark.asyncio
    async def test_group_by_with_count_passes_guard(self) -> None:
        """GROUP BY + COUNT on large table must not be blocked."""
        from src.services.agents.internal_tools.database_tools import internal_query_database

        result = await internal_query_database(
            connection_id=_GUARD_CONN_ID,
            query=("SELECT n % 5 AS bucket, COUNT(*) AS cnt FROM big_table GROUP BY bucket ORDER BY bucket"),
            tenant_id=_GUARD_TENANT_ID,
            db_session=_make_mock_session(_GUARD_DB_CONN),
        )

        assert result["success"] is True, f"GROUP BY query should pass: {result}"
        rows = result["data"]
        assert len(rows) == 5
        for row in rows:
            assert row["cnt"] == 20_000

    @pytest.mark.asyncio
    async def test_small_table_not_blocked(self) -> None:
        """A broad SELECT on a small table (< 50K rows) must pass through.

        small_table (100 rows) is created in setup_class alongside big_table.
        CREATE TABLE is blocked by the write guard in internal_query_database,
        so the table must be seeded directly via the connector in setup_class.
        """
        from src.services.agents.internal_tools.database_tools import internal_query_database

        result = await internal_query_database(
            connection_id=_GUARD_CONN_ID,
            query="SELECT * FROM small_table",
            tenant_id=_GUARD_TENANT_ID,
            db_session=_make_mock_session(_GUARD_DB_CONN),
        )

        assert result["success"] is True, f"Small table SELECT should pass: {result}"
        assert result["row_count"] == 100
