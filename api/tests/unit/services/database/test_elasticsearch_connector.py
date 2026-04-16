from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from elasticsearch.exceptions import NotFoundError

from src.models.database_connection import DatabaseConnection
from src.services.database.elasticsearch_connector import ElasticsearchConnector


class TestElasticsearchConnector:
    @pytest.fixture
    def mock_db_connection(self):
        conn = MagicMock(spec=DatabaseConnection)
        conn.host = "localhost"
        conn.port = 9200
        conn.username = "user"
        conn.password_encrypted = "enc_pass"
        conn.connection_params = {"use_ssl": False}
        return conn

    @pytest.fixture
    def connector(self, mock_db_connection):
        return ElasticsearchConnector(mock_db_connection)

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.info = AsyncMock()
        client.close = AsyncMock()
        client.search = AsyncMock()
        client.count = AsyncMock()
        client.cat = MagicMock()
        client.cat.indices = AsyncMock()
        client.indices = MagicMock()
        client.indices.get_mapping = AsyncMock()
        client.indices.get_settings = AsyncMock()
        client.cluster = MagicMock()
        client.cluster.health = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_connect_success(self, connector, mock_client):
        with (
            patch("src.services.database.elasticsearch_connector.decrypt_value", return_value="password"),
            patch(
                "src.services.database.elasticsearch_connector.AsyncElasticsearch", return_value=mock_client
            ) as mock_es,
        ):
            mock_client.info.return_value = {"version": "8.0"}

            result = await connector.connect()

            assert result is True
            assert connector.client == mock_client
            mock_es.assert_called_once()
            mock_client.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, connector):
        with (
            patch("src.services.database.elasticsearch_connector.decrypt_value", return_value="password"),
            patch("src.services.database.elasticsearch_connector.AsyncElasticsearch") as mock_es,
        ):
            mock_es.side_effect = Exception("Connection error")

            result = await connector.connect()

            assert result is False
            assert connector.client is None

    @pytest.mark.asyncio
    async def test_disconnect(self, connector, mock_client):
        connector.client = mock_client
        await connector.disconnect()

        mock_client.close.assert_called_once()
        assert connector.client is None

    @pytest.mark.asyncio
    async def test_execute_search_success(self, connector, mock_client):
        connector.client = mock_client

        mock_client.search.return_value = {
            "took": 10,
            "hits": {
                "total": {"value": 1},
                "hits": [{"_index": "idx", "_id": "1", "_score": 1.0, "_source": {"field": "val"}}],
            },
        }

        result = await connector.execute_search("idx", {"query": {}})

        assert result["success"] is True
        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["_source"] == {"field": "val"}

    @pytest.mark.asyncio
    async def test_execute_search_error(self, connector, mock_client):
        connector.client = mock_client
        mock_client.search.side_effect = Exception("Search error")

        result = await connector.execute_search("idx", {})

        assert result["success"] is False
        assert "Search error" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_count(self, connector, mock_client):
        connector.client = mock_client
        mock_client.count.return_value = {"count": 100}

        result = await connector.execute_count("idx", {"match_all": {}})

        assert result["success"] is True
        assert result["count"] == 100

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector, mock_client):
        with (
            patch.object(connector, "connect", return_value=True),
            patch.object(connector, "disconnect", new_callable=AsyncMock),
        ):
            connector.client = mock_client
            mock_client.info.return_value = {"cluster_name": "docker-cluster", "version": {"number": "8.0.0"}}
            mock_client.cluster.health.return_value = {
                "status": "green",
                "number_of_nodes": 1,
                "number_of_data_nodes": 1,
            }

            result = await connector.test_connection()

            assert result["success"] is True
            assert result["details"]["cluster_name"] == "docker-cluster"
            assert result["details"]["status"] == "green"

    @pytest.mark.asyncio
    async def test_get_indices(self, connector, mock_client):
        connector.client = mock_client
        mock_client.cat.indices.return_value = [{"index": "idx1", "status": "open", "docs.count": "10"}]

        result = await connector.get_indices()

        assert result["success"] is True
        assert len(result["indices"]) == 1
        assert result["indices"][0]["name"] == "idx1"
        assert result["indices"][0]["docs_count"] == 10

    @pytest.mark.asyncio
    async def test_get_index_mapping(self, connector, mock_client):
        connector.client = mock_client
        mock_client.indices.get_mapping.return_value = {
            "idx1": {"mappings": {"properties": {"field1": {"type": "text"}}}}
        }

        result = await connector.get_index_mapping("idx1")

        assert result["success"] is True
        assert result["index"] == "idx1"
        assert len(result["fields"]) == 1
        assert result["fields"][0]["name"] == "field1"
        assert result["fields"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_get_index_mapping_not_found(self, connector, mock_client):
        connector.client = mock_client
        # Provide required args for NotFoundError (message, meta, body)
        mock_client.indices.get_mapping.side_effect = NotFoundError("Index not found", MagicMock(), {})

        result = await connector.get_index_mapping("idx1")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_index_settings(self, connector, mock_client):
        connector.client = mock_client
        mock_client.indices.get_settings.return_value = {"idx1": {"settings": {"index": {"number_of_shards": "1"}}}}

        result = await connector.get_index_settings("idx1")

        assert result["success"] is True
        assert result["settings"]["index"]["number_of_shards"] == "1"

    @pytest.mark.asyncio
    async def test_get_sample_documents(self, connector):
        with patch.object(connector, "execute_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"success": True, "results": []}

            await connector.get_sample_documents("idx1", size=5)

            mock_search.assert_called_once()
            args = mock_search.call_args
            assert args[0][0] == "idx1"
            assert args[1]["size"] == 5

    @pytest.mark.asyncio
    async def test_execute_aggregation(self, connector, mock_client):
        connector.client = mock_client
        mock_client.search.return_value = {"took": 5, "aggregations": {"agg1": {"value": 10}}}

        result = await connector.execute_aggregation("idx1", {"agg1": {"terms": {"field": "f1"}}})

        assert result["success"] is True
        assert result["aggregations"] == {"agg1": {"value": 10}}
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args[1]
        assert call_args["body"]["size"] == 0
