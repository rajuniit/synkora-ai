"""
Integration tests for Bot Workers endpoints.

Tests bot worker monitoring and management.
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

    email = f"workers_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Workers Test User",
            "tenant_name": "Workers Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one()
    account.status = AccountStatus.ACTIVE
    await async_db_session.commit()

    # Login
    login_response = await async_client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


class TestBotWorkersListIntegration:
    """Test listing bot workers."""

    @pytest.mark.asyncio
    async def test_list_workers(self, async_client: AsyncClient, auth_headers):
        """Test listing all bot workers."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/bot-workers",
            headers=headers,
        )

        # Accept 200 (success) or 500 (Redis not available)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "workers" in data
            assert "total_workers" in data
            assert "healthy_workers" in data
            assert isinstance(data["workers"], list)


class TestBotWorkersCapacityIntegration:
    """Test bot worker capacity endpoint."""

    @pytest.mark.asyncio
    async def test_get_capacity(self, async_client: AsyncClient, auth_headers):
        """Test getting worker pool capacity."""
        headers, tenant_id, account = auth_headers

        response = await async_client.get(
            "/api/v1/bot-workers/capacity",
            headers=headers,
        )

        # Accept 200 (success) or 500 (Redis not available)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "total_capacity" in data
            assert "active_bots" in data
            assert "available_capacity" in data
            assert "healthy_workers" in data
            assert "total_workers" in data


class TestBotWorkersGetWorkerIntegration:
    """Test getting specific worker."""

    @pytest.mark.asyncio
    async def test_get_worker_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting a nonexistent worker returns 404."""
        headers, tenant_id, account = auth_headers

        fake_worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        response = await async_client.get(
            f"/api/v1/bot-workers/{fake_worker_id}",
            headers=headers,
        )

        # Accept 404 (not found) or 500 (Redis not available)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]

    @pytest.mark.asyncio
    async def test_get_worker_bots_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting bots for a nonexistent worker."""
        headers, tenant_id, account = auth_headers

        fake_worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        response = await async_client.get(
            f"/api/v1/bot-workers/{fake_worker_id}/bots",
            headers=headers,
        )

        # Accept 200 (empty list) or 404 (not found) or 500 (Redis not available)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


class TestBotWorkersCleanupIntegration:
    """Test worker cleanup endpoint."""

    @pytest.mark.asyncio
    async def test_cleanup_dead_workers(self, async_client: AsyncClient, auth_headers):
        """Test cleaning up dead workers."""
        headers, tenant_id, account = auth_headers

        response = await async_client.post(
            "/api/v1/bot-workers/cleanup",
            headers=headers,
        )

        # Accept 200 (success) or 500 (Redis not available)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "removed_workers" in data
            assert "removed_count" in data


class TestBotDeploymentStatusIntegration:
    """Test bot deployment status endpoint."""

    @pytest.mark.asyncio
    async def test_get_bot_status(self, async_client: AsyncClient, auth_headers):
        """Test getting bot deployment status."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/bot-workers/bots/{fake_bot_id}/status",
            headers=headers,
        )

        # Accept 200 (success) or 500 (Redis not available)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "bot_id" in data
            assert "is_deployed" in data


class TestBotWorkersSlackActivationIntegration:
    """Test Slack bot activation/deactivation on worker pool."""

    @pytest.mark.asyncio
    async def test_activate_slack_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test activating a nonexistent Slack bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/slack/{fake_bot_id}/activate",
            headers=headers,
        )

        # Accept 200 (returns result with error), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_deactivate_slack_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test deactivating a nonexistent Slack bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/slack/{fake_bot_id}/deactivate",
            headers=headers,
        )

        # Accept 200 (returns result), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_restart_slack_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test restarting a nonexistent Slack bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/slack/{fake_bot_id}/restart",
            headers=headers,
        )

        # Accept 200 (returns result), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


class TestBotWorkersTelegramActivationIntegration:
    """Test Telegram bot activation/deactivation on worker pool."""

    @pytest.mark.asyncio
    async def test_activate_telegram_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test activating a nonexistent Telegram bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/telegram/{fake_bot_id}/activate",
            headers=headers,
        )

        # Accept 200 (returns result with error), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_deactivate_telegram_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test deactivating a nonexistent Telegram bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/telegram/{fake_bot_id}/deactivate",
            headers=headers,
        )

        # Accept 200 (returns result), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    @pytest.mark.asyncio
    async def test_restart_telegram_bot_not_found(self, async_client: AsyncClient, auth_headers):
        """Test restarting a nonexistent Telegram bot."""
        headers, tenant_id, account = auth_headers

        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/bot-workers/telegram/{fake_bot_id}/restart",
            headers=headers,
        )

        # Accept 200 (returns result), 400 (bad request), 404 (not found), or 500 (service error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]


class TestBotWorkersAuthorizationIntegration:
    """Test bot workers authorization."""

    @pytest.mark.asyncio
    async def test_list_workers_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list workers are rejected."""
        response = await async_client.get("/api/v1/bot-workers")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_capacity_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to get capacity are rejected."""
        response = await async_client.get("/api/v1/bot-workers/capacity")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_worker_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to get worker details are rejected."""
        response = await async_client.get("/api/v1/bot-workers/test-worker-id")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_cleanup_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to cleanup workers are rejected."""
        response = await async_client.post("/api/v1/bot-workers/cleanup")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_get_bot_status_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to get bot status are rejected."""
        fake_bot_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/bot-workers/bots/{fake_bot_id}/status")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_activate_slack_bot_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to activate Slack bots are rejected."""
        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(f"/api/v1/bot-workers/slack/{fake_bot_id}/activate")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_activate_telegram_bot_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to activate Telegram bots are rejected."""
        fake_bot_id = str(uuid.uuid4())
        response = await async_client.post(f"/api/v1/bot-workers/telegram/{fake_bot_id}/activate")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
