"""
Tests for elasticsearch_tools.py - Elasticsearch Search Tools

Tests the Elasticsearch tools for searching indices, listing indices,
and getting index statistics.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestInternalElasticsearchSearch:
    """Tests for internal_elasticsearch_search function."""

    @pytest.mark.asyncio
    async def test_requires_connection_name(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        result = await internal_elasticsearch_search(
            connection_name="",
            index_pattern="logs_*",
            query="error",
        )

        assert result["success"] is False
        assert "Connection name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_index_pattern(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        result = await internal_elasticsearch_search(
            connection_name="Main ES",
            index_pattern="",
            query="error",
        )

        assert result["success"] is False
        assert "Index pattern is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_query(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        result = await internal_elasticsearch_search(
            connection_name="Main ES",
            index_pattern="logs_*",
            query="",
        )

        assert result["success"] is False
        assert "Query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        result = await internal_elasticsearch_search(
            connection_name="Main ES",
            index_pattern="logs_*",
            query="error",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "No runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_tenant_id_in_context(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        mock_context = MagicMock(spec=[])  # Object without tenant_id

        result = await internal_elasticsearch_search(
            connection_name="Main ES",
            index_pattern="logs_*",
            query="error",
            runtime_context=mock_context,
        )

        assert result["success"] is False
        assert "tenant ID" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_connection(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_context = MagicMock()
        mock_context.tenant_id = "tenant-123"
        mock_context.db_session = mock_db

        result = await internal_elasticsearch_search(
            connection_name="Nonexistent ES",
            index_pattern="logs_*",
            query="error",
            runtime_context=mock_context,
        )

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_inactive_connection(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_search

        mock_connection = MagicMock()
        mock_connection.status = "inactive"

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_context = MagicMock()
        mock_context.tenant_id = "tenant-123"
        mock_context.db_session = mock_db

        result = await internal_elasticsearch_search(
            connection_name="Main ES",
            index_pattern="logs_*",
            query="error",
            runtime_context=mock_context,
        )

        assert result["success"] is False
        assert "not active" in result["error"]


class TestInternalElasticsearchListIndices:
    """Tests for internal_elasticsearch_list_indices function."""

    @pytest.mark.asyncio
    async def test_requires_connection_name(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_list_indices

        result = await internal_elasticsearch_list_indices(connection_name="")

        assert result["success"] is False
        assert "Connection name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_list_indices

        result = await internal_elasticsearch_list_indices(
            connection_name="Main ES",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "No runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_tenant_id(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_list_indices

        mock_context = MagicMock(spec=[])

        result = await internal_elasticsearch_list_indices(
            connection_name="Main ES",
            runtime_context=mock_context,
        )

        assert result["success"] is False
        assert "tenant ID" in result["error"]


class TestInternalElasticsearchGetIndexStats:
    """Tests for internal_elasticsearch_get_index_stats function."""

    @pytest.mark.asyncio
    async def test_requires_connection_name(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_get_index_stats

        result = await internal_elasticsearch_get_index_stats(
            connection_name="",
            index_pattern="logs_*",
        )

        assert result["success"] is False
        assert "Connection name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_index_pattern(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_get_index_stats

        result = await internal_elasticsearch_get_index_stats(
            connection_name="Main ES",
            index_pattern="",
        )

        assert result["success"] is False
        assert "Index pattern is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.elasticsearch_tools import internal_elasticsearch_get_index_stats

        result = await internal_elasticsearch_get_index_stats(
            connection_name="Main ES",
            index_pattern="logs_*",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "No runtime context" in result["error"]
