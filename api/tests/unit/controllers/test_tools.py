"""Tests for tools controller."""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.tools import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.id = uuid.uuid4()
    account.email = "test@example.com"
    return account


@pytest.fixture
def client(mock_db_session, mock_tenant_id, mock_account):
    # Patch AuthService.check_permission to always return True for admin checks
    with patch("src.middleware.auth_middleware.AuthService.check_permission", return_value=True):
        app = FastAPI()
        app.include_router(router)

        async def mock_db():
            yield mock_db_session

        app.dependency_overrides[get_async_db] = mock_db
        app.dependency_overrides[get_current_tenant_id] = lambda: mock_tenant_id
        app.dependency_overrides[get_current_account] = lambda: mock_account
        yield TestClient(app)


class TestGetToolConfigurations:
    """Tests for getting tool configurations."""

    def test_get_tool_configurations_success(self, client):
        """Test successfully getting tool configurations."""
        with patch.dict(
            os.environ,
            {
                "SERPAPI_KEY": "test_serp_key_12345678",
                "GITHUB_TOKEN": "test_github_token",
                "YOUTUBE_API_KEY": "test_youtube_key",
            },
        ):
            response = client.get("/tools/config")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "web_search" in data
        assert "github" in data
        assert "youtube" in data
        # Values should be masked
        assert "****" in data["web_search"]["SERPAPI_KEY"]

    def test_get_tool_configurations_empty(self, client):
        """Test getting configurations when none are set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear specific keys
            for key in ["SERPAPI_KEY", "GITHUB_TOKEN", "YOUTUBE_API_KEY", "GMAIL_CREDENTIALS_PATH"]:
                os.environ.pop(key, None)

            response = client.get("/tools/config")

        assert response.status_code == status.HTTP_200_OK


class TestSaveToolConfiguration:
    """Tests for saving tool configurations."""

    def test_save_tool_configuration_success(self, client):
        """Test successfully saving tool configuration."""
        with patch("src.controllers.tools._update_env_file"):
            response = client.post(
                "/tools/config", json={"tool": "web_search", "config": {"SERPAPI_KEY": "new_key_value"}}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "web_search" in data["message"]


class TestTestToolConfiguration:
    """Tests for testing tool configurations."""

    def test_test_web_search_success(self, client):
        """Test testing web search configuration."""
        with patch("src.controllers.tools._test_web_search", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "message": "Web search is working correctly"}

            response = client.post("/tools/test/web_search", json={"SERPAPI_KEY": "test_key"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_test_github_success(self, client):
        """Test testing GitHub configuration."""
        with patch("src.controllers.tools._test_github", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "message": "GitHub integration is working correctly"}

            response = client.post("/tools/test/github", json={"GITHUB_TOKEN": "test_token"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_test_youtube_success(self, client):
        """Test testing YouTube configuration."""
        with patch("src.controllers.tools._test_youtube", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "message": "YouTube integration is working correctly"}

            response = client.post("/tools/test/youtube", json={"YOUTUBE_API_KEY": "test_key"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_test_gmail_success(self, client):
        """Test testing Gmail configuration."""
        with patch("src.controllers.tools._test_gmail", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "message": "Gmail credentials file found"}

            response = client.post("/tools/test/GMAIL", json={"GMAIL_CREDENTIALS_PATH": "/path/to/creds.json"})

        assert response.status_code == status.HTTP_200_OK

    def test_test_unknown_tool(self, client):
        """Test testing unknown tool."""
        response = client.post("/tools/test/unknown_tool", json={})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert "Unknown tool" in data["error"]

    def test_test_tool_failure(self, client):
        """Test tool configuration test failure."""
        with patch("src.controllers.tools._test_web_search", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": False, "error": "API key invalid"}

            response = client.post("/tools/test/web_search", json={"SERPAPI_KEY": "invalid_key"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
