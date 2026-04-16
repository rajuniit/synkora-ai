"""Tests for charts controller."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.charts import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def client(mock_db_session):
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies - use async generator for db
    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db

    # Mock current account
    mock_account = MagicMock()
    mock_account.id = uuid.uuid4()
    app.dependency_overrides[get_current_account] = lambda: mock_account

    # Mock tenant ID
    tenant_id = uuid.uuid4()
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    return TestClient(app), tenant_id, mock_account, mock_db_session


def _create_mock_chart(chart_id, tenant_id, agent_id, **kwargs):
    """Helper to create mock chart."""
    mock_chart = MagicMock()
    mock_chart.id = chart_id
    mock_chart.tenant_id = tenant_id
    mock_chart.agent_id = agent_id
    mock_chart.conversation_id = kwargs.get("conversation_id")
    mock_chart.message_id = kwargs.get("message_id")
    mock_chart.title = kwargs.get("title", "Test Chart")
    mock_chart.description = kwargs.get("description")
    mock_chart.chart_type = kwargs.get("chart_type", "bar")
    mock_chart.library = kwargs.get("library", "chartjs")
    mock_chart.config = kwargs.get("config", {"options": {}})
    mock_chart.data = kwargs.get("data", {"labels": [], "datasets": []})
    mock_chart.query = kwargs.get("query")
    mock_chart.created_at = datetime.now(UTC)
    mock_chart.updated_at = datetime.now(UTC)
    return mock_chart


class TestCreateChart:
    """Tests for creating charts."""

    def test_create_chart_success(self, client):
        """Test successful chart creation."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        # Mock the chart that would be created
        _create_mock_chart(chart_id, tenant_id, agent_id)

        # Need to mock the add and return the chart on refresh
        async def mock_refresh(chart):
            chart.id = chart_id
            chart.created_at = datetime.now(UTC)
            chart.updated_at = datetime.now(UTC)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/charts",
            json={
                "agent_id": str(agent_id),
                "title": "Test Chart",
                "chart_type": "bar",
                "library": "chartjs",
                "config": {"options": {"responsive": True}},
                "data": {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        mock_db.add.assert_called_once()

    def test_create_chart_with_conversation(self, client):
        """Test creating chart associated with a conversation."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        message_id = uuid.uuid4()

        async def mock_refresh(chart):
            chart.id = chart_id
            chart.created_at = datetime.now(UTC)
            chart.updated_at = datetime.now(UTC)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        response = test_client.post(
            "/charts",
            json={
                "agent_id": str(agent_id),
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
                "title": "Conversation Chart",
                "chart_type": "line",
                "library": "chartjs",
                "config": {},
                "data": {"labels": [], "datasets": []},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED


class TestListCharts:
    """Tests for listing charts."""

    def test_list_charts_success(self, client):
        """Test listing all charts."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_chart]
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get("/charts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_charts_filter_by_agent(self, client):
        """Test listing charts filtered by agent."""
        test_client, tenant_id, mock_account, mock_db = client

        agent_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(f"/charts?agent_id={agent_id}")

        assert response.status_code == status.HTTP_200_OK

    def test_list_charts_filter_by_conversation(self, client):
        """Test listing charts filtered by conversation."""
        test_client, tenant_id, mock_account, mock_db = client

        conversation_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(f"/charts?conversation_id={conversation_id}")

        assert response.status_code == status.HTTP_200_OK


class TestGetChart:
    """Tests for getting a specific chart."""

    def test_get_chart_success(self, client):
        """Test getting a specific chart."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(f"/charts/{chart_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(chart_id)

    def test_get_chart_not_found(self, client):
        """Test getting non-existent chart."""
        test_client, tenant_id, mock_account, mock_db = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(f"/charts/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateChart:
    """Tests for updating charts."""

    def test_update_chart_success(self, client):
        """Test updating a chart."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id, title="Updated Chart")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.patch(f"/charts/{chart_id}", json={"title": "Updated Chart"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Chart"

    def test_update_chart_not_found(self, client):
        """Test updating non-existent chart."""
        test_client, tenant_id, mock_account, mock_db = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.patch(f"/charts/{uuid.uuid4()}", json={"title": "Updated"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_chart_config(self, client):
        """Test updating chart config."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute = AsyncMock(return_value=mock_result)

        new_config = {"options": {"responsive": True, "scales": {"y": {"beginAtZero": True}}}}

        response = test_client.patch(f"/charts/{chart_id}", json={"config": new_config})

        assert response.status_code == status.HTTP_200_OK

    def test_update_chart_data(self, client):
        """Test updating chart data."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute = AsyncMock(return_value=mock_result)

        new_data = {"labels": ["Jan", "Feb", "Mar"], "datasets": [{"data": [10, 20, 30]}]}

        response = test_client.patch(f"/charts/{chart_id}", json={"data": new_data})

        assert response.status_code == status.HTTP_200_OK


class TestDeleteChart:
    """Tests for deleting charts."""

    def test_delete_chart_success(self, client):
        """Test deleting a chart."""
        test_client, tenant_id, mock_account, mock_db = client

        chart_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        mock_chart = _create_mock_chart(chart_id, tenant_id, agent_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_chart
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(f"/charts/{chart_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_chart_not_found(self, client):
        """Test deleting non-existent chart."""
        test_client, tenant_id, mock_account, mock_db = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(f"/charts/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
