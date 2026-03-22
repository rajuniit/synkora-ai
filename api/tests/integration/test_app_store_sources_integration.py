"""
Integration tests for App Store Sources endpoints.

Tests app store review source CRUD, sync, and analysis operations.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, async_db_session: AsyncSession):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    email = f"appstore_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "App Store Test User",
            "tenant_name": "App Store Test Org",
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

    # Login
    login_response = await async_client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


class TestAppStoreSourcesListIntegration:
    """Test listing app store sources."""

    @pytest.mark.asyncio
    async def test_list_app_store_sources(self, async_client: AsyncClient, auth_headers):
        """Test listing all app store sources."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/app-store-sources",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestAppStoreSourcesCRUDIntegration:
    """Test app store source CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_app_store_source(self, async_client: AsyncClient, auth_headers):
        """Test creating an app store source."""
        headers, tenant_id, account = auth_headers

        source_data = {
            "app_name": f"Test App {uuid.uuid4().hex[:8]}",
            "store_type": "apple_app_store",
            "app_id": "com.example.testapp",
            "languages": ["en"],
            "countries": ["us"],
        }

        response = await async_client.post(
            "/api/v1/app-store-sources",
            json=source_data,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            data = response.json()
            assert data["app_name"] == source_data["app_name"]
            assert data["store_type"] == source_data["store_type"]

    @pytest.mark.asyncio
    async def test_create_app_store_source_google_play(self, async_client: AsyncClient, auth_headers):
        """Test creating a Google Play store source."""
        headers, tenant_id, account = auth_headers

        source_data = {
            "app_name": f"Google Play App {uuid.uuid4().hex[:8]}",
            "store_type": "google_play",
            "app_id": "com.example.androidapp",
            "languages": ["en"],
            "countries": ["us"],
        }

        response = await async_client.post(
            "/api/v1/app-store-sources",
            json=source_data,
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_get_app_store_source_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting a nonexistent app store source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/app-store-sources/{fake_source_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_app_store_source_not_found(self, async_client: AsyncClient, auth_headers):
        """Test updating a nonexistent app store source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        update_data = {"app_name": "Updated Name"}

        response = await async_client.patch(
            f"/api/v1/app-store-sources/{fake_source_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_app_store_source_not_found(self, async_client: AsyncClient, auth_headers):
        """Test deleting a nonexistent app store source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/app-store-sources/{fake_source_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAppStoreSourcesSyncIntegration:
    """Test app store source sync operations."""

    @pytest.mark.asyncio
    async def test_sync_app_store_source_not_found(self, async_client: AsyncClient, auth_headers):
        """Test syncing a nonexistent app store source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/app-store-sources/{fake_source_id}/sync",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAppStoreSourcesInsightsIntegration:
    """Test app store source insights operations."""

    @pytest.mark.asyncio
    async def test_get_insights_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting insights for nonexistent source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/app-store-sources/{fake_source_id}/insights",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAppStoreSourcesReviewsIntegration:
    """Test app store source reviews listing."""

    @pytest.mark.asyncio
    async def test_list_reviews_not_found(self, async_client: AsyncClient, auth_headers):
        """Test listing reviews for nonexistent source returns 404."""
        headers, tenant_id, account = auth_headers

        fake_source_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/app-store-sources/{fake_source_id}/reviews",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAppStoreSourcesAuthorizationIntegration:
    """Test app store sources authorization."""

    @pytest.mark.asyncio
    async def test_list_sources_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list sources are rejected."""
        response = await async_client.get("/api/v1/app-store-sources")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_create_source_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to create sources are rejected."""
        source_data = {
            "app_name": "Unauthorized Source",
            "store_type": "apple_app_store",
            "app_id": "com.example.testapp",
        }

        response = await async_client.post(
            "/api/v1/app-store-sources",
            json=source_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_sync_source_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to sync sources are rejected."""
        fake_source_id = str(uuid.uuid4())
        response = await async_client.post(f"/api/v1/app-store-sources/{fake_source_id}/sync")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_delete_source_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to delete sources are rejected."""
        fake_source_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/app-store-sources/{fake_source_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
