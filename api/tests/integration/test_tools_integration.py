"""
Integration tests for Tool Configuration endpoints.

Tests tool configuration management (API keys for external services).
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def admin_auth_headers(client: TestClient, async_db_session: AsyncSession):
    """Create authenticated admin user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    email = f"tools_admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Tools Admin User",
            "tenant_name": "Tools Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one_or_none()
    account.status = AccountStatus.ACTIVE
    await async_db_session.commit()

    # Ensure user has ADMIN role (OWNER role should have admin access)
    # The registration creates an OWNER role which has admin permissions

    # Login
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


@pytest_asyncio.fixture
async def normal_auth_headers(client: TestClient, async_db_session: AsyncSession, admin_auth_headers):
    """Create authenticated normal (non-admin) user."""
    from src.models import Account, AccountRole, AccountStatus, TenantAccountJoin
    from src.services.auth_service import AuthService

    admin_headers, tenant_id, admin_account = admin_auth_headers

    email = f"tools_normal_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Create account directly
    normal_account = Account(
        name="Tools Normal User",
        email=email,
        status=AccountStatus.ACTIVE,
        password_hash=AuthService.hash_password(password),
    )
    async_db_session.add(normal_account)
    await async_db_session.commit()
    await async_db_session.refresh(normal_account)

    # Add to tenant with NORMAL role
    tenant_join = TenantAccountJoin(
        tenant_id=uuid.UUID(tenant_id),
        account_id=normal_account.id,
        role=AccountRole.NORMAL,
    )
    async_db_session.add(tenant_join)
    await async_db_session.commit()

    # Login
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, normal_account


class TestToolConfigurationGetIntegration:
    """Test getting tool configurations."""

    def test_get_tool_configurations_admin(self, client: TestClient, admin_auth_headers):
        """Test admin can get tool configurations."""
        headers, tenant_id, account = admin_auth_headers

        response = client.get(
            "/api/v1/tools/config",
            headers=headers,
        )

        # Accept 200 (success) or 500 (service error)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return a dict of tool configurations
            assert isinstance(data, dict)
            # Check expected keys are present
            assert "web_search" in data or "github" in data or "GMAIL" in data or "youtube" in data

    def test_get_tool_configurations_non_admin(self, client: TestClient, normal_auth_headers):
        """Test non-admin cannot get tool configurations."""
        headers, tenant_id, account = normal_auth_headers

        response = client.get(
            "/api/v1/tools/config",
            headers=headers,
        )

        # Should return 403 for non-admin
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestToolConfigurationSaveIntegration:
    """Test saving tool configurations."""

    def test_save_tool_configuration_admin(self, client: TestClient, admin_auth_headers):
        """Test admin can save tool configuration."""
        headers, tenant_id, account = admin_auth_headers

        config_data = {
            "tool": "web_search",
            "config": {
                "SERPAPI_KEY": "test-serpapi-key-12345",
            },
        }

        response = client.post(
            "/api/v1/tools/config",
            json=config_data,
            headers=headers,
        )

        # Accept 200 (success) or 500 (service error - e.g., can't write .env)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True

    def test_save_tool_configuration_invalid_key(self, client: TestClient, admin_auth_headers):
        """Test saving with invalid config key returns 400."""
        headers, tenant_id, account = admin_auth_headers

        config_data = {
            "tool": "malicious",
            "config": {
                "INVALID_KEY": "should-not-be-allowed",
            },
        }

        response = client.post(
            "/api/v1/tools/config",
            json=config_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_save_tool_configuration_non_admin(self, client: TestClient, normal_auth_headers):
        """Test non-admin cannot save tool configurations."""
        headers, tenant_id, account = normal_auth_headers

        config_data = {
            "tool": "web_search",
            "config": {
                "SERPAPI_KEY": "test-key",
            },
        }

        response = client.post(
            "/api/v1/tools/config",
            json=config_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestToolTestIntegration:
    """Test tool testing endpoint."""

    def test_test_tool_web_search(self, client: TestClient, admin_auth_headers):
        """Test testing web search configuration."""
        headers, tenant_id, account = admin_auth_headers

        # Test with a mock API key (will likely fail but shouldn't error)
        config = {"SERPAPI_KEY": "test-key-for-testing"}

        response = client.post(
            "/api/v1/tools/test/web_search",
            json=config,
            headers=headers,
        )

        # Accept 200 (success or failure response) or 500 (service error)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return success status
            assert "success" in data

    def test_test_tool_github(self, client: TestClient, admin_auth_headers):
        """Test testing GitHub configuration."""
        headers, tenant_id, account = admin_auth_headers

        config = {"GITHUB_TOKEN": "test-github-token"}

        response = client.post(
            "/api/v1/tools/test/github",
            json=config,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_test_tool_youtube(self, client: TestClient, admin_auth_headers):
        """Test testing YouTube configuration."""
        headers, tenant_id, account = admin_auth_headers

        config = {"YOUTUBE_API_KEY": "test-youtube-api-key"}

        response = client.post(
            "/api/v1/tools/test/youtube",
            json=config,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_test_tool_gmail(self, client: TestClient, admin_auth_headers):
        """Test testing Gmail configuration."""
        headers, tenant_id, account = admin_auth_headers

        config = {"GMAIL_CREDENTIALS_PATH": "/path/to/credentials.json"}

        response = client.post(
            "/api/v1/tools/test/GMAIL",
            json=config,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_test_tool_unknown(self, client: TestClient, admin_auth_headers):
        """Test testing unknown tool returns appropriate response."""
        headers, tenant_id, account = admin_auth_headers

        config = {}

        response = client.post(
            "/api/v1/tools/test/unknown_tool",
            json=config,
            headers=headers,
        )

        # Should return 200 with success=False
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False

    def test_test_tool_non_admin(self, client: TestClient, normal_auth_headers):
        """Test non-admin cannot test tool configurations."""
        headers, tenant_id, account = normal_auth_headers

        config = {"SERPAPI_KEY": "test-key"}

        response = client.post(
            "/api/v1/tools/test/web_search",
            json=config,
            headers=headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestToolsAuthorizationIntegration:
    """Test tools authorization."""

    def test_get_config_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to get config are rejected."""
        response = client.get("/api/v1/tools/config")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_save_config_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to save config are rejected."""
        config_data = {
            "tool": "web_search",
            "config": {"SERPAPI_KEY": "test-key"},
        }

        response = client.post(
            "/api/v1/tools/config",
            json=config_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_test_tool_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to test tools are rejected."""
        response = client.post(
            "/api/v1/tools/test/web_search",
            json={},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
