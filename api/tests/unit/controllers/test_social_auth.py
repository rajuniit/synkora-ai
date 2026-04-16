"""Tests for social auth controller."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.social_auth import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = uuid.uuid4()
    account.email = "test@example.com"
    account.name = "Test User"
    return account


@pytest.fixture
def client(mock_db_session):
    app = FastAPI()
    app.include_router(router)

    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db

    yield TestClient(app), mock_db_session


@pytest.fixture
def authenticated_client(mock_db_session, mock_account):
    app = FastAPI()
    app.include_router(router)

    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db
    app.dependency_overrides[get_current_account] = lambda: mock_account

    yield TestClient(app), mock_db_session, mock_account


def _create_mock_provider_config(enabled=True):
    """Helper to create mock provider config."""
    config = MagicMock()
    config.client_id = "test_client_id"
    config.client_secret = "encrypted_secret"
    config.redirect_uri = "https://example.com/callback"
    config.enabled = enabled
    config.config = {}
    return config


def _create_mock_platform_tenant():
    """Helper to create mock platform tenant."""
    from src.models.tenant import TenantType

    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.name = "Platform Tenant"
    tenant.tenant_type = TenantType.PLATFORM
    return tenant


class TestGoogleLogin:
    """Tests for Google OAuth login."""

    def test_google_login_no_platform_tenant(self, client):
        """Test error when platform tenant doesn't exist."""
        test_client, mock_db = client

        # Mock execute to return None for platform tenant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = test_client.get("/api/v1/auth/google/login")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Platform tenant not found" in response.json()["detail"]


class TestMicrosoftLogin:
    """Tests for Microsoft OAuth login."""

    def test_microsoft_login_no_platform_tenant(self, client):
        """Test error when platform tenant doesn't exist."""
        test_client, mock_db = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = test_client.get("/api/v1/auth/microsoft/login")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAppleLogin:
    """Tests for Apple OAuth login."""

    def test_apple_login_no_platform_tenant(self, client):
        """Test error when platform tenant doesn't exist."""
        test_client, mock_db = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = test_client.get("/api/v1/auth/apple/login")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGoogleCallback:
    """Tests for Google OAuth callback."""

    def test_google_callback_invalid_state(self, client):
        """Test callback with invalid state."""
        test_client, mock_db = client

        # Mock _get_oauth_state to return None (invalid/expired state)
        with patch("src.controllers.social_auth._get_oauth_state", return_value=None):
            response = test_client.get("/api/v1/auth/google/callback?code=auth_code&state=invalid_state")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired state" in response.json()["detail"]


class TestMicrosoftCallback:
    """Tests for Microsoft OAuth callback."""

    def test_microsoft_callback_invalid_state(self, client):
        """Test callback with invalid state."""
        test_client, mock_db = client

        # Mock _get_oauth_state to return None (invalid/expired state)
        with patch("src.controllers.social_auth._get_oauth_state", return_value=None):
            response = test_client.get("/api/v1/auth/microsoft/callback?code=auth_code&state=invalid_state")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired state" in response.json()["detail"]


class TestAppleCallback:
    """Tests for Apple OAuth callback."""

    def test_apple_callback_invalid_state(self, client):
        """Test callback with invalid state via POST."""
        test_client, mock_db = client

        # Mock _get_oauth_state to return None (invalid/expired state)
        with patch("src.controllers.social_auth._get_oauth_state", return_value=None):
            response = test_client.post(
                "/api/v1/auth/apple/callback", data={"code": "auth_code", "state": "invalid_state"}
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
