from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chart import Chart
from src.services.charts.chart_service import ChartService


class TestChartService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db):
        return ChartService(mock_db)

    @pytest.mark.asyncio
    async def test_create_chart_chartjs(self, service, mock_db):
        tenant_id = uuid4()
        data = {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]}

        chart = await service.create_chart(
            tenant_id=tenant_id, title="Test Chart", chart_type="bar", data=data, library="chartjs"
        )

        assert chart.tenant_id == tenant_id
        assert chart.library == "chartjs"
        assert chart.config["type"] == "bar"
        assert chart.config["data"]["labels"] == ["A", "B"]
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_chart_plotly(self, service, mock_db):
        tenant_id = uuid4()
        data = {"x": [1, 2], "y": [3, 4]}

        chart = await service.create_chart(
            tenant_id=tenant_id, title="Test Chart", chart_type="line", data=data, library="plotly"
        )

        assert chart.library == "plotly"
        assert chart.config["data"][0]["type"] == "scatter"  # line maps to scatter in plotly logic

    @pytest.mark.asyncio
    async def test_create_chart_unsupported_library(self, service, mock_db):
        with pytest.raises(ValueError, match="Unsupported chart library"):
            await service.create_chart(tenant_id=uuid4(), title="Test", chart_type="bar", data={}, library="unknown")

    @pytest.mark.asyncio
    async def test_get_chart_found(self, service, mock_db):
        chart_id = uuid4()
        tenant_id = uuid4()
        mock_chart = MagicMock(spec=Chart)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute.return_value = mock_result

        result = await service.get_chart(chart_id, tenant_id)
        assert result == mock_chart

    @pytest.mark.asyncio
    async def test_get_chart_not_found(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_chart(uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_charts(self, service, mock_db):
        mock_charts = [MagicMock(spec=Chart), MagicMock(spec=Chart)]
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_charts
        mock_db.execute.return_value = mock_result

        result = await service.list_charts(uuid4(), agent_id=uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_delete_chart_success(self, service, mock_db):
        mock_chart = MagicMock(spec=Chart)
        with patch.object(service, "get_chart", return_value=mock_chart):
            result = await service.delete_chart(uuid4(), uuid4())
            assert result is True
            mock_db.delete.assert_called_once_with(mock_chart)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_chart_not_found(self, service, mock_db):
        with patch.object(service, "get_chart", return_value=None):
            result = await service.delete_chart(uuid4(), uuid4())
            assert result is False
            mock_db.delete.assert_not_called()

    def test_generate_chart_from_query_result(self, service):
        query_result = [{"category": "A", "value": 10}, {"category": "B", "value": 20}]

        # Test auto-detection
        data = service.generate_chart_from_query_result(query_result)
        assert data["labels"] == ["A", "B"]
        assert data["datasets"][0]["data"] == [10.0, 20.0]
        assert data["datasets"][0]["label"] == "value"

        # Test specified columns
        data = service.generate_chart_from_query_result(query_result, x_column="category", y_column="value")
        assert data["labels"] == ["A", "B"]

    def test_generate_chart_from_query_result_empty(self, service):
        data = service.generate_chart_from_query_result([])
        assert data["labels"] == []
        assert data["datasets"] == []

    def test_generate_chart_from_query_result_error(self, service):
        query_result = [{"col1": 1}]  # Only 1 column
        with pytest.raises(ValueError, match="at least 2 columns"):
            service.generate_chart_from_query_result(query_result)

    def test_generate_colors(self, service):
        colors = service._generate_colors(12)
        assert len(colors) == 12
        assert colors[0] == colors[10]  # Colors repeat (10 base colors)
