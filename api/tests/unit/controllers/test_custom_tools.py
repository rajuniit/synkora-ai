"""Tests for custom tools controller."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.custom_tools import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id


@pytest.fixture
def mock_openapi_parser():
    with patch("src.controllers.custom_tools.OpenAPIParser") as mock:
        yield mock


@pytest.fixture
def mock_tool_executor():
    with patch("src.controllers.custom_tools.ToolExecutor") as mock:
        yield mock


@pytest.fixture
def mock_encrypt_value():
    with patch("src.controllers.custom_tools.encrypt_value") as mock:
        mock.side_effect = lambda x: f"encrypted_{x}"
        yield mock


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def client(mock_db_session, mock_openapi_parser, mock_encrypt_value):
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies - use async generator for db
    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db

    # Mock tenant ID
    tenant_id = uuid.uuid4()
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    return TestClient(app), tenant_id, mock_db_session, mock_openapi_parser


def _get_sample_openapi_schema():
    """Return a sample OpenAPI schema for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0", "description": "Test API"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
    }


def _create_mock_custom_tool(tool_id, tenant_id, **kwargs):
    """Helper to create mock custom tool."""
    mock_tool = MagicMock()
    mock_tool.id = tool_id
    mock_tool.tenant_id = tenant_id
    mock_tool.name = kwargs.get("name", "Test Tool")
    mock_tool.description = kwargs.get("description", "Test description")
    mock_tool.openapi_schema = kwargs.get("openapi_schema", _get_sample_openapi_schema())
    mock_tool.server_url = kwargs.get("server_url", "https://api.example.com")
    mock_tool.auth_type = kwargs.get("auth_type", "none")
    mock_tool.auth_config = kwargs.get("auth_config", {})
    mock_tool.enabled = kwargs.get("enabled", True)
    mock_tool.icon = kwargs.get("icon")
    mock_tool.tags = kwargs.get("tags", [])
    mock_tool.created_at = datetime.now(UTC)
    mock_tool.updated_at = datetime.now(UTC)
    return mock_tool


class TestCreateCustomTool:
    """Tests for creating custom tools."""

    def test_create_custom_tool_success(self, client):
        """Test successful custom tool creation."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()

        # Mock parser
        parser_instance = mock_parser.return_value
        parser_instance.get_schema_info.return_value = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test API",
            "server_url": "https://api.example.com",
            "operation_count": 1,
        }

        # Mock no existing tool with same name - use async execute pattern
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock add
        def mock_add(tool):
            tool.id = tool_id
            tool.created_at = datetime.now(UTC)
            tool.updated_at = datetime.now(UTC)

        mock_db.add = MagicMock(side_effect=mock_add)

        response = test_client.post(
            "/custom-tools",
            json={
                "name": "Test Tool",
                "description": "Test description",
                "openapi_schema": _get_sample_openapi_schema(),
                "auth_type": "none",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Tool"

    def test_create_custom_tool_duplicate_name(self, client):
        """Test creating tool with duplicate name."""
        test_client, tenant_id, mock_db, mock_parser = client

        # Mock parser
        parser_instance = mock_parser.return_value
        parser_instance.get_schema_info.return_value = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test API",
            "server_url": "https://api.example.com",
            "operation_count": 1,
        }

        # Mock existing tool with same name
        existing_tool = _create_mock_custom_tool(uuid.uuid4(), tenant_id, name="Test Tool")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            "/custom-tools", json={"name": "Test Tool", "openapi_schema": _get_sample_openapi_schema()}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_custom_tool_invalid_schema(self, client):
        """Test creating tool with invalid OpenAPI schema."""
        test_client, tenant_id, mock_db, mock_parser = client

        # Mock parser raising error
        mock_parser.side_effect = Exception("Invalid schema")

        response = test_client.post(
            "/custom-tools", json={"name": "Test Tool", "openapi_schema": {"invalid": "schema"}}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_custom_tool_with_auth(self, client):
        """Test creating tool with authentication config."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()

        parser_instance = mock_parser.return_value
        parser_instance.get_schema_info.return_value = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test API",
            "server_url": "https://api.example.com",
            "operation_count": 1,
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        def mock_add(tool):
            tool.id = tool_id
            tool.created_at = datetime.now(UTC)
            tool.updated_at = datetime.now(UTC)

        mock_db.add = MagicMock(side_effect=mock_add)

        response = test_client.post(
            "/custom-tools",
            json={
                "name": "Auth Tool",
                "openapi_schema": _get_sample_openapi_schema(),
                "auth_type": "bearer",
                "auth_config": {"token": "secret-token"},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED


class TestListCustomTools:
    """Tests for listing custom tools."""

    def test_list_custom_tools_success(self, client):
        """Test listing all custom tools."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_tool]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock parser for operation count
        parser_instance = mock_parser.return_value
        parser_instance.get_available_operations.return_value = [{"operation_id": "getUsers"}]

        response = test_client.get("/custom-tools")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_custom_tools_enabled_only(self, client):
        """Test listing only enabled custom tools."""
        test_client, tenant_id, mock_db, mock_parser = client

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        parser_instance = mock_parser.return_value
        parser_instance.get_available_operations.return_value = []

        response = test_client.get("/custom-tools?enabled_only=true")

        assert response.status_code == status.HTTP_200_OK


class TestGetCustomTool:
    """Tests for getting a specific custom tool."""

    def test_get_custom_tool_success(self, client):
        """Test getting a specific custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        parser_instance = mock_parser.return_value
        parser_instance.get_schema_info.return_value = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test API",
            "server_url": "https://api.example.com",
            "operation_count": 1,
        }
        parser_instance.get_available_operations.return_value = [
            {"operation_id": "getUsers", "method": "GET", "path": "/users"}
        ]

        response = test_client.get(f"/custom-tools/{tool_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(tool_id)

    def test_get_custom_tool_not_found(self, client):
        """Test getting non-existent custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.get(f"/custom-tools/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateCustomTool:
    """Tests for updating custom tools."""

    def test_update_custom_tool_success(self, client):
        """Test updating a custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        # First query returns the tool to update, second query for duplicate name check returns None
        mock_result_tool = MagicMock()
        mock_result_tool.scalar_one_or_none.return_value = mock_tool
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[mock_result_tool, mock_result_none])

        parser_instance = mock_parser.return_value
        parser_instance.get_available_operations.return_value = [{"operation_id": "getUsers"}]

        response = test_client.put(f"/custom-tools/{tool_id}", json={"name": "Updated Tool Name"})

        assert response.status_code == status.HTTP_200_OK

    def test_update_custom_tool_not_found(self, client):
        """Test updating non-existent custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.put(f"/custom-tools/{uuid.uuid4()}", json={"name": "Updated"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_custom_tool_duplicate_name(self, client):
        """Test updating tool to duplicate name."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        other_tool_id = uuid.uuid4()

        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)
        existing_tool = _create_mock_custom_tool(other_tool_id, tenant_id, name="Existing Tool")

        # First call returns the tool being updated, second call returns existing tool with same name
        mock_result_tool = MagicMock()
        mock_result_tool.scalar_one_or_none.return_value = mock_tool
        mock_result_existing = MagicMock()
        mock_result_existing.scalar_one_or_none.return_value = existing_tool
        mock_db.execute = AsyncMock(side_effect=[mock_result_tool, mock_result_existing])

        response = test_client.put(f"/custom-tools/{tool_id}", json={"name": "Existing Tool"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeleteCustomTool:
    """Tests for deleting custom tools."""

    def test_delete_custom_tool_success(self, client):
        """Test deleting a custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(f"/custom-tools/{tool_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_db.delete.assert_called_once()

    def test_delete_custom_tool_not_found(self, client):
        """Test deleting non-existent custom tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.delete(f"/custom-tools/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListToolOperations:
    """Tests for listing tool operations."""

    def test_list_operations_success(self, client):
        """Test listing operations for a tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        parser_instance = mock_parser.return_value
        parser_instance.get_available_operations.return_value = [
            {
                "operation_id": "getUsers",
                "method": "GET",
                "path": "/users",
                "summary": "Get users",
                "description": "Get all users",
                "parameters": [],
                "request_body": None,
                "tags": [],
            }
        ]

        response = test_client.get(f"/custom-tools/{tool_id}/operations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["operation_id"] == "getUsers"


class TestTestTool:
    """Tests for testing custom tools."""

    def test_test_tool_connection(self, client, mock_tool_executor):
        """Test testing tool connection."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        executor_instance = mock_tool_executor.return_value
        executor_instance.test_connection = AsyncMock(return_value={"success": True, "message": "Connected"})

        response = test_client.post(f"/custom-tools/{tool_id}/test", json={})

        assert response.status_code == status.HTTP_200_OK

    def test_test_tool_operation(self, client, mock_tool_executor):
        """Test testing a specific operation."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        executor_instance = mock_tool_executor.return_value
        executor_instance.execute = AsyncMock(return_value={"users": []})

        response = test_client.post(
            f"/custom-tools/{tool_id}/test", json={"operation_id": "getUsers", "parameters": {}}
        )

        assert response.status_code == status.HTTP_200_OK


class TestExecuteToolOperation:
    """Tests for executing tool operations."""

    def test_execute_operation_success(self, client, mock_tool_executor):
        """Test executing a tool operation."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id, enabled=True)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        executor_instance = mock_tool_executor.return_value
        executor_instance.execute = AsyncMock(return_value={"users": [{"id": 1, "name": "John"}]})

        response = test_client.post(
            f"/custom-tools/{tool_id}/execute", json={"operation_id": "getUsers", "parameters": {}}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_execute_operation_tool_disabled(self, client, mock_tool_executor):
        """Test executing operation on disabled tool."""
        test_client, tenant_id, mock_db, mock_parser = client

        tool_id = uuid.uuid4()
        mock_tool = _create_mock_custom_tool(tool_id, tenant_id, enabled=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = test_client.post(
            f"/custom-tools/{tool_id}/execute", json={"operation_id": "getUsers", "parameters": {}}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
