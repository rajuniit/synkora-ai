from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.database_connection import DatabaseConnection
from src.services.database.postgresql_connector import PostgreSQLConnector


class TestPostgreSQLConnector:
    @pytest.fixture
    def mock_db_connection(self):
        conn = MagicMock(spec=DatabaseConnection)
        conn.host = "localhost"
        conn.port = 5432
        conn.database_name = "test_db"
        conn.username = "user"
        conn.password_encrypted = "enc_pass"
        conn.connection_params = {}
        return conn

    @pytest.fixture
    def connector(self, mock_db_connection):
        return PostgreSQLConnector(mock_db_connection)

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        pool.close = AsyncMock()
        pool.acquire = MagicMock()
        return pool

    @pytest.fixture
    def mock_conn(self):
        conn = MagicMock()
        conn.fetch = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.fetchval = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_connect_success(self, connector, mock_pool):
        with (
            patch("src.services.database.postgresql_connector.decrypt_value", return_value="password"),
            patch(
                "src.services.database.postgresql_connector.asyncpg.create_pool", new_callable=AsyncMock
            ) as mock_create_pool,
        ):
            mock_create_pool.return_value = mock_pool

            result = await connector.connect()

            assert result is True
            assert connector.pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, connector):
        with (
            patch("src.services.database.postgresql_connector.decrypt_value", return_value="password"),
            patch(
                "src.services.database.postgresql_connector.asyncpg.create_pool",
                side_effect=Exception("Connection failed"),
            ),
        ):
            result = await connector.connect()

            assert result is False
            assert connector.pool is None

    @pytest.mark.asyncio
    async def test_disconnect(self, connector, mock_pool):
        connector.pool = mock_pool
        await connector.disconnect()

        mock_pool.close.assert_called_once()
        assert connector.pool is None

    @pytest.mark.asyncio
    async def test_execute_query_success(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool

        # Setup context manager for pool.acquire()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Setup fetch return value
        # asyncpg Record objects behave like dicts
        mock_conn.fetch.return_value = [{"id": 1, "name": "test"}]

        result = await connector.execute_query("SELECT * FROM users")

        assert result["success"] is True
        assert result["rows"] == [{"id": 1, "name": "test"}]
        assert result["row_count"] == 1
        assert result["columns"] == ["id", "name"]
        mock_conn.fetch.assert_called_once_with("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_execute_query_with_params(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        result = await connector.execute_query("SELECT * FROM users WHERE id = $1", [1])

        assert result["success"] is True
        mock_conn.fetch.assert_called_once_with("SELECT * FROM users WHERE id = $1", 1)

    @pytest.mark.asyncio
    async def test_execute_query_error(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.side_effect = Exception("Query error")

        result = await connector.execute_query("SELECT * FROM users")

        assert result["success"] is False
        assert "Query error" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_count(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 42

        result = await connector.execute_count("SELECT COUNT(*) FROM users")

        assert result["success"] is True
        assert result["count"] == 42

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector, mock_pool, mock_conn):
        with (
            patch.object(connector, "connect", return_value=True),
            patch.object(connector, "disconnect", new_callable=AsyncMock),
            patch.object(connector, "get_connection") as mock_get_conn,
        ):
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchrow.side_effect = [{"version": "PostgreSQL 14"}, {"size": 1024}]

            result = await connector.test_connection()

            assert result["success"] is True
            assert result["details"]["version"] == "PostgreSQL 14"
            assert result["details"]["database_size_bytes"] == 1024

    @pytest.mark.asyncio
    async def test_get_tables(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = [{"table_name": "t1"}, {"table_name": "t2"}]

        tables = await connector.get_tables()

        assert tables == ["t1", "t2"]

    @pytest.mark.asyncio
    async def test_get_schema(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # First fetch returns tables
        # Second fetch returns columns for table 1
        mock_conn.fetch.side_effect = [
            [{"table_name": "users", "table_type": "BASE TABLE"}],
            [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None},
                {"column_name": "name", "data_type": "text", "is_nullable": "YES", "column_default": None},
            ],
        ]

        result = await connector.get_schema()

        assert result["success"] is True
        assert len(result["tables"]) == 1
        table = result["tables"][0]
        assert table["name"] == "users"
        assert len(table["columns"]) == 2
        assert table["columns"][0]["name"] == "id"
        assert table["columns"][0]["nullable"] is False

    @pytest.mark.asyncio
    async def test_get_table_info(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Sequential calls: get_tables (for validation), columns, pks, fks, count
        mock_conn.fetch.side_effect = [
            [{"table_name": "users", "table_type": "BASE TABLE"}],  # get_tables for validation
            [
                {
                    "column_name": "id",
                    "data_type": "int",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                }
            ],
            [{"attname": "id"}],
            [],
        ]
        mock_conn.fetchval.return_value = 10

        result = await connector.get_table_info("users")

        assert result["success"] is True
        assert result["table_name"] == "users"
        assert result["primary_keys"] == ["id"]
        assert result["row_count"] == 10

    @pytest.mark.asyncio
    async def test_get_sample_data(self, connector, mock_pool, mock_conn):
        connector.pool = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock get_tables for validation, then the actual query
        mock_conn.fetch.side_effect = [
            [{"table_name": "users", "table_type": "BASE TABLE"}],  # get_tables for validation
        ]

        with patch.object(connector, "execute_query", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "rows": []}

            await connector.get_sample_data("users", limit=5)

            mock_execute.assert_called_once()
            args = mock_execute.call_args[0]
            assert "LIMIT $1" in args[0]
            assert args[1] == [5]
