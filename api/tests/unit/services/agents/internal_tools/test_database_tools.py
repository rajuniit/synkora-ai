from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database_connection import DatabaseConnection
from src.services.agents.internal_tools.database_tools import (
    internal_generate_chart,
    internal_get_database_schema,
    internal_list_database_connections,
    internal_query_and_chart,
    internal_query_database,
)


class TestDatabaseTools:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock(spec=DatabaseConnection)
        conn.id = uuid4()
        conn.tenant_id = uuid4()
        conn.name = "Test DB"
        conn.database_type = "POSTGRESQL"
        conn.status = "active"
        conn.host = "localhost"
        conn.port = 5432
        conn.database_name = "test_db"
        return conn

    @pytest.mark.asyncio
    async def test_internal_query_database_postgres(self, mock_db_session, mock_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.PostgreSQLConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.execute_query = AsyncMock(
                return_value={"rows": [{"id": 1}], "row_count": 1, "columns": ["id"]}
            )
            connector_instance.disconnect = AsyncMock()

            result = await internal_query_database(
                str(mock_connection.id), "SELECT * FROM users", str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["data"] == [{"id": 1}]
            assert result["database_type"] == "postgresql"
            connector_instance.execute_query.assert_called_with("SELECT * FROM users")

    @pytest.mark.asyncio
    async def test_internal_query_database_elasticsearch(self, mock_db_session, mock_connection):
        mock_connection.database_type = "ELASTICSEARCH"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.ElasticsearchConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.execute_search = AsyncMock(
                return_value={
                    "success": True,
                    "total": 1,
                    "results": [{"_index": "test", "_id": "1", "_score": 1.0, "_source": {"id": 1}}],
                }
            )
            connector_instance.disconnect = AsyncMock()

            # Valid DSL query
            dsl_query = '{"index": "test", "query": {"match_all": {}}}'
            result = await internal_query_database(
                str(mock_connection.id), dsl_query, str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["database_type"] == "elasticsearch"

            # Invalid JSON query (natural language)
            result = await internal_query_database(
                str(mock_connection.id), "find me users", str(mock_connection.tenant_id), mock_db_session
            )
            assert result["success"] is False
            assert "Natural language queries" in result["error"]

    @pytest.mark.asyncio
    async def test_internal_query_database_sqlite(self, mock_db_session, mock_connection):
        mock_connection.database_type = "SQLITE"
        mock_connection.database_path = "/tmp/test.db"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.SQLiteConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.execute_query = AsyncMock(
                return_value={"rows": [{"id": 1}], "row_count": 1, "columns": ["id"]}
            )
            connector_instance.disconnect = AsyncMock()

            result = await internal_query_database(
                str(mock_connection.id), "SELECT * FROM users", str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["database_type"] == "sqlite"

    @pytest.mark.asyncio
    async def test_internal_query_database_not_found(self, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await internal_query_database(str(uuid4()), "query", str(uuid4()), mock_db_session)
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_internal_query_database_inactive(self, mock_db_session, mock_connection):
        mock_connection.status = "inactive"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await internal_query_database(
            str(mock_connection.id), "query", str(mock_connection.tenant_id), mock_db_session
        )
        assert result["success"] is False
        assert "not active" in result["error"]

    @pytest.mark.asyncio
    async def test_internal_list_database_connections(self, mock_db_session, mock_connection):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_connection]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await internal_list_database_connections(str(mock_connection.tenant_id), mock_db_session)

        assert result["success"] is True
        assert len(result["connections"]) == 1
        assert result["connections"][0]["name"] == "Test DB"

    @pytest.mark.asyncio
    async def test_internal_get_database_schema_postgres(self, mock_db_session, mock_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.PostgreSQLConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.get_tables = AsyncMock(return_value=["users"])
            connector_instance.get_table_info = AsyncMock(return_value={"name": "users", "columns": []})
            connector_instance.disconnect = AsyncMock()

            result = await internal_get_database_schema(
                str(mock_connection.id), str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["schema"]["total_tables"] == 1
            assert result["schema"]["tables"][0]["name"] == "users"

    @pytest.mark.asyncio
    async def test_internal_get_database_schema_elasticsearch(self, mock_db_session, mock_connection):
        mock_connection.database_type = "ELASTICSEARCH"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.ElasticsearchConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.get_indices = AsyncMock(
                return_value={
                    "success": True,
                    "indices": [{"name": "users", "health": "green", "status": "open", "docs_count": 0}],
                }
            )
            connector_instance.get_index_mapping = AsyncMock(return_value={"success": True, "fields": []})
            connector_instance.disconnect = AsyncMock()

            result = await internal_get_database_schema(
                str(mock_connection.id), str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["schema"]["total_indices"] == 1
            assert result["schema"]["indices"][0]["index"] == "users"

    @pytest.mark.asyncio
    async def test_internal_get_database_schema_sqlite(self, mock_db_session, mock_connection):
        mock_connection.database_type = "SQLITE"
        mock_connection.database_path = "/tmp/test.db"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.internal_tools.database_tools.SQLiteConnector") as MockConnector:
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.get_schema = AsyncMock(return_value={"success": True, "tables": [{"name": "users"}]})
            connector_instance.disconnect = AsyncMock()

            result = await internal_get_database_schema(
                str(mock_connection.id), str(mock_connection.tenant_id), mock_db_session
            )

            assert result["success"] is True
            assert result["schema"]["total_tables"] == 1
            assert result["schema"]["tables"][0]["name"] == "users"

    @pytest.mark.asyncio
    async def test_internal_generate_chart(self, mock_db_session):
        query_result = {
            "success": True,
            "data": [{"date": "2023-01-01", "value": 10}],
            "row_count": 1,
            "connection_name": "Test DB",
        }

        mock_chart_instance = MagicMock()
        mock_chart_instance.id = uuid4()
        mock_chart_instance.chart_type = "bar"
        mock_chart_instance.library = "chartjs"
        mock_chart_instance.config = {}
        mock_chart_instance.data = {}

        mock_new_session = AsyncMock()
        mock_new_session.add = MagicMock()
        mock_new_session.refresh = AsyncMock()
        mock_new_session.__aenter__ = AsyncMock(return_value=mock_new_session)
        mock_new_session.__aexit__ = AsyncMock(return_value=False)

        mock_txn = AsyncMock()
        mock_txn.__aenter__ = AsyncMock(return_value=mock_txn)
        mock_txn.__aexit__ = AsyncMock(return_value=False)
        mock_new_session.begin = MagicMock(return_value=mock_txn)

        mock_session_factory = MagicMock(return_value=mock_new_session)
        mock_get_factory = MagicMock(return_value=mock_session_factory)

        with (
            patch("src.services.agents.internal_tools.database_tools.ChartService") as MockChartService,
            patch("src.services.agents.internal_tools.database_tools.Chart") as MockChart,
            patch("src.core.database.get_async_session_factory", mock_get_factory),
        ):
            service_instance = MockChartService.return_value
            service_instance.generate_chart_from_query_result.return_value = {"labels": [], "datasets": []}
            service_instance._generate_chart_config.return_value = {}

            MockChart.return_value = mock_chart_instance

            # Simulate refresh populating chart attributes
            async def refresh_side_effect(obj):
                obj.id = mock_chart_instance.id
                obj.chart_type = "bar"
                obj.library = "chartjs"
                obj.config = {}
                obj.data = {}

            mock_new_session.refresh.side_effect = refresh_side_effect

            result = await internal_generate_chart(
                query_result, "bar", "My Chart", str(uuid4()), str(uuid4()), mock_db_session
            )

            assert result["success"] is True
            assert result["chart_id"] == str(mock_chart_instance.id)

    @pytest.mark.asyncio
    async def test_internal_generate_chart_no_data(self, mock_db_session):
        query_result = {"data": []}
        result = await internal_generate_chart(
            query_result, "bar", "Title", str(uuid4()), str(uuid4()), mock_db_session
        )
        assert result["success"] is False
        assert "No data" in result["error"]

    @pytest.mark.asyncio
    async def test_internal_query_and_chart(self, mock_db_session, mock_connection):
        # Mock query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        mock_chart_instance2 = MagicMock()
        mock_chart_instance2.id = uuid4()
        mock_chart_instance2.chart_type = "bar"
        mock_chart_instance2.library = "chartjs"
        mock_chart_instance2.config = {}
        mock_chart_instance2.data = {}

        mock_new_session2 = AsyncMock()
        mock_new_session2.add = MagicMock()
        mock_new_session2.refresh = AsyncMock()
        mock_new_session2.__aenter__ = AsyncMock(return_value=mock_new_session2)
        mock_new_session2.__aexit__ = AsyncMock(return_value=False)

        mock_txn2 = AsyncMock()
        mock_txn2.__aenter__ = AsyncMock(return_value=mock_txn2)
        mock_txn2.__aexit__ = AsyncMock(return_value=False)
        mock_new_session2.begin = MagicMock(return_value=mock_txn2)

        mock_session_factory2 = MagicMock(return_value=mock_new_session2)
        mock_get_factory2 = MagicMock(return_value=mock_session_factory2)

        with (
            patch("src.services.agents.internal_tools.database_tools.PostgreSQLConnector") as MockConnector,
            patch("src.services.agents.internal_tools.database_tools.ChartService") as MockChartService,
            patch("src.services.agents.internal_tools.database_tools.Chart") as MockChart2,
            patch("src.core.database.get_async_session_factory", mock_get_factory2),
        ):
            # Setup query result
            connector_instance = MockConnector.return_value
            connector_instance.connect = AsyncMock()
            connector_instance.execute_query = AsyncMock(
                return_value={"rows": [{"val": 10}], "row_count": 1, "columns": ["val"]}
            )
            connector_instance.disconnect = AsyncMock()

            # Setup chart service
            service_instance = MockChartService.return_value
            service_instance.generate_chart_from_query_result.return_value = {}
            service_instance._generate_chart_config.return_value = {}

            MockChart2.return_value = mock_chart_instance2

            async def refresh_side_effect2(obj):
                obj.id = mock_chart_instance2.id
                obj.chart_type = "bar"
                obj.library = "chartjs"
                obj.config = {}
                obj.data = {}

            mock_new_session2.refresh.side_effect = refresh_side_effect2

            result = await internal_query_and_chart(
                str(mock_connection.id), "query", "Title", str(mock_connection.tenant_id), str(uuid4()), mock_db_session
            )

            assert result["success"] is True
            assert result["chart"]["success"] is True
