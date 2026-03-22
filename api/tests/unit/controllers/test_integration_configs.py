"""Tests for integration configs controller."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.integration_configs import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id


@pytest.fixture
def mock_integration_config_service():
    with patch("src.controllers.integration_configs.IntegrationConfigService") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def mock_permission_service():
    with patch("src.controllers.integration_configs.PermissionService") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def mock_email_service():
    with patch("src.controllers.integration_configs.EmailService") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def client(mock_integration_config_service, mock_permission_service, mock_email_service, mock_db_session):
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies
    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db

    # Mock current account
    mock_account = MagicMock()
    mock_account.id = uuid.uuid4()
    mock_account.email = "test@example.com"
    app.dependency_overrides[get_current_account] = lambda: mock_account

    # Mock tenant ID
    tenant_id = uuid.uuid4()
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    return (
        TestClient(app),
        tenant_id,
        mock_account,
        mock_db_session,
        {"config": mock_integration_config_service, "permission": mock_permission_service, "email": mock_email_service},
    )


def _create_mock_config(config_id, tenant_id, **kwargs):
    """Helper to create mock integration config."""
    mock_config = MagicMock()
    mock_config.id = config_id
    mock_config.tenant_id = tenant_id
    mock_config.integration_type = kwargs.get("integration_type", "email")
    mock_config.provider = kwargs.get("provider", "smtp")
    mock_config.is_active = kwargs.get("is_active", True)
    mock_config.is_default = kwargs.get("is_default", False)
    mock_config.is_platform_config = kwargs.get("is_platform_config", False)
    mock_config.created_at = datetime.now(UTC)
    mock_config.updated_at = datetime.now(UTC)
    return mock_config


class TestListConfigs:
    """Tests for listing integration configs."""

    def test_list_configs_success(self, client):
        """Test listing integration configs."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        # Mock permissions
        mock_permission.check_permission.return_value = True

        # Mock configs
        mock_config = _create_mock_config(uuid.uuid4(), tenant_id)
        mock_config_service.list_configs.return_value = [mock_config]

        response = test_client.get("/console/api/integration-configs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_configs_filter_type(self, client):
        """Test listing configs filtered by type."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        mock_permission.check_permission.return_value = True
        mock_config_service.list_configs.return_value = []

        response = test_client.get("/console/api/integration-configs?integration_type=email")

        assert response.status_code == status.HTTP_200_OK

    def test_list_configs_permission_denied(self, client):
        """Test listing configs without permission."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_permission = mocks["permission"].return_value

        mock_permission.check_permission.return_value = False

        response = test_client.get("/console/api/integration-configs")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetConfig:
    """Tests for getting a specific config."""

    def test_get_config_success(self, client):
        """Test getting a specific config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id)
        mock_config_service.get_config.return_value = mock_config
        mock_config_service.get_config_data.return_value = {"smtp_host": "smtp.example.com"}
        mock_permission.check_permission.return_value = True

        response = test_client.get(f"/console/api/integration-configs/{config_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(config_id)

    def test_get_config_not_found(self, client):
        """Test getting non-existent config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value

        mock_config_service.get_config.return_value = None

        response = test_client.get(f"/console/api/integration-configs/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_config_wrong_tenant(self, client):
        """Test getting config from different tenant."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        other_tenant_id = uuid.uuid4()
        mock_config = _create_mock_config(uuid.uuid4(), other_tenant_id)
        mock_config_service.get_config.return_value = mock_config
        mock_permission.check_permission.return_value = True

        response = test_client.get(f"/console/api/integration-configs/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCreateConfig:
    """Tests for creating configs."""

    def test_create_config_success(self, client):
        """Test creating a config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id)
        mock_config_service.create_config.return_value = mock_config
        mock_permission.check_permission.return_value = True

        response = test_client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                "provider": "smtp",
                "config_data": {"smtp_host": "smtp.example.com", "smtp_port": 587},
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data

    def test_create_config_missing_fields(self, client):
        """Test creating config with missing fields."""
        test_client, tenant_id, mock_account, mock_db, mocks = client

        response = test_client.post("/console/api/integration-configs", json={"integration_type": "email"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_platform_config_permission_denied(self, client):
        """Test creating platform config without permission."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_permission = mocks["permission"].return_value

        mock_permission.check_permission.return_value = False

        response = test_client.post(
            "/console/api/integration-configs",
            json={
                "integration_type": "email",
                "provider": "smtp",
                "config_data": {"smtp_host": "smtp.example.com"},
                "is_platform_config": True,
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUpdateConfig:
    """Tests for updating configs."""

    def test_update_config_success(self, client):
        """Test updating a config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id)
        mock_config_service.get_config.return_value = mock_config
        mock_config_service.update_config.return_value = mock_config
        mock_permission.check_permission.return_value = True

        response = test_client.put(
            f"/console/api/integration-configs/{config_id}", json={"config_data": {"smtp_host": "new-smtp.example.com"}}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_config_not_found(self, client):
        """Test updating non-existent config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value

        mock_config_service.get_config.return_value = None

        response = test_client.put(f"/console/api/integration-configs/{uuid.uuid4()}", json={"config_data": {}})

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteConfig:
    """Tests for deleting configs."""

    def test_delete_config_success(self, client):
        """Test deleting a config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id)
        mock_config_service.get_config.return_value = mock_config
        mock_config_service.delete_config.return_value = True
        mock_permission.check_permission.return_value = True

        response = test_client.delete(f"/console/api/integration-configs/{config_id}")

        assert response.status_code == status.HTTP_200_OK

    def test_delete_config_not_found(self, client):
        """Test deleting non-existent config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value

        mock_config_service.get_config.return_value = None

        response = test_client.delete(f"/console/api/integration-configs/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTestConfig:
    """Tests for testing config connections."""

    def test_test_config_success(self, client):
        """Test testing a config connection."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_email_service = mocks["email"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id, integration_type="email")
        mock_config_service.get_config.return_value = mock_config
        mock_permission.check_permission.return_value = True
        mock_email_service.test_connection.return_value = {"success": True, "message": "Connected"}

        response = test_client.post(
            f"/console/api/integration-configs/{config_id}/test", json={"test_email": "test@example.com"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_test_config_non_email(self, client):
        """Test testing non-email config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id, integration_type="storage")
        mock_config_service.get_config.return_value = mock_config
        mock_permission.check_permission.return_value = True

        response = test_client.post(f"/console/api/integration-configs/{config_id}/test", json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetActiveConfig:
    """Tests for getting active config."""

    def test_get_active_config_success(self, client):
        """Test getting active config."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        config_id = uuid.uuid4()
        mock_config = _create_mock_config(config_id, tenant_id, is_active=True)
        mock_config_service.get_active_config.return_value = mock_config
        mock_config_service.get_active_config_data.return_value = {"smtp_host": "smtp.example.com"}
        mock_permission.check_permission.return_value = True

        response = test_client.get("/console/api/integration-configs/active?integration_type=email")

        assert response.status_code == status.HTTP_200_OK

    def test_get_active_config_not_found(self, client):
        """Test getting active config when none exists."""
        test_client, tenant_id, mock_account, mock_db, mocks = client
        mock_config_service = mocks["config"].return_value
        mock_permission = mocks["permission"].return_value

        mock_config_service.get_active_config.return_value = None
        mock_permission.check_permission.return_value = True

        response = test_client.get("/console/api/integration-configs/active?integration_type=email")

        assert response.status_code == status.HTTP_404_NOT_FOUND
