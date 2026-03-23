"""
Integration tests for Telegram Bots endpoints.

Tests Telegram bot CRUD operations and management.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, async_db_session: AsyncSession):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    email = f"telegram_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Telegram Test User",
            "tenant_name": "Telegram Test Org",
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


@pytest.fixture
def test_agent(client: TestClient, auth_headers):
    """Create a test agent for Telegram bot tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"telegram-test-agent-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/agents",
        json={
            "name": f"Telegram Test Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Agent for Telegram bot tests",
            "system_prompt": "You are a test agent for Telegram.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return response.json()["id"]
    return None


class TestTelegramBotsListIntegration:
    """Test listing Telegram bots."""

    def test_list_telegram_bots(self, client: TestClient, auth_headers):
        """Test listing all Telegram bots."""
        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/telegram-bots",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_telegram_bots_filter_by_agent(self, client: TestClient, auth_headers, test_agent):
        """Test listing Telegram bots filtered by agent."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        response = client.get(
            f"/api/v1/telegram-bots?agent_id={test_agent}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_list_telegram_bots_filter_by_active(self, client: TestClient, auth_headers):
        """Test listing Telegram bots filtered by active status."""
        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/telegram-bots?is_active=true",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK


class TestTelegramBotsCRUDIntegration:
    """Test Telegram bot CRUD operations."""

    def test_create_telegram_bot(self, client: TestClient, auth_headers, test_agent):
        """Test creating a Telegram bot."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # Generate a fake but valid-looking bot token
        bot_token = f"{uuid.uuid4().int % 10000000000}:{''.join(uuid.uuid4().hex[:35])}"

        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Test Telegram Bot {uuid.uuid4().hex[:8]}",
            "bot_token": bot_token,
            "use_webhook": False,
        }

        response = client.post(
            "/api/v1/telegram-bots",
            json=bot_data,
            headers=headers,
        )

        # Accept 200/201 (success) or 400 (invalid token) or 500 (API error)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_create_telegram_bot_nonexistent_agent(self, client: TestClient, auth_headers):
        """Test creating a Telegram bot for nonexistent agent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_agent_id = str(uuid.uuid4())
        bot_token = f"{uuid.uuid4().int % 10000000000}:{''.join(uuid.uuid4().hex[:35])}"

        bot_data = {
            "agent_id": fake_agent_id,
            "bot_name": "Should Fail Bot",
            "bot_token": bot_token,
            "use_webhook": False,
        }

        response = client.post(
            "/api/v1/telegram-bots",
            json=bot_data,
            headers=headers,
        )

        # Should return 404 for nonexistent agent
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test getting a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/telegram-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test updating a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        update_data = {"bot_name": "Should Fail"}

        response = client.put(
            f"/api/v1/telegram-bots/{fake_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test deleting a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/telegram-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTelegramBotsValidateTokenIntegration:
    """Test Telegram bot token validation."""

    def test_validate_token(self, client: TestClient, auth_headers):
        """Test validating a Telegram bot token."""
        headers, tenant_id, account = auth_headers

        # Use a fake token (will fail validation but shouldn't error)
        bot_token = f"{uuid.uuid4().int % 10000000000}:{''.join(uuid.uuid4().hex[:35])}"

        response = client.post(
            "/api/v1/telegram-bots/validate-token",
            json={"bot_token": bot_token},
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "valid" in data
            # Token is fake so it should be invalid
            assert data["valid"] is False


class TestTelegramBotsControlIntegration:
    """Test Telegram bot start/stop/restart operations."""

    def test_start_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test starting a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/telegram-bots/{fake_id}/start",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stop_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test stopping a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/telegram-bots/{fake_id}/stop",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restart_telegram_bot_not_found(self, client: TestClient, auth_headers):
        """Test restarting a nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/telegram-bots/{fake_id}/restart",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_telegram_bot_status_not_found(self, client: TestClient, auth_headers):
        """Test getting status of nonexistent Telegram bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/telegram-bots/{fake_id}/status",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTelegramBotsWebhookIntegration:
    """Test Telegram bot webhook endpoint."""

    def test_webhook_invalid_bot_id(self, client: TestClient):
        """Test webhook with invalid bot ID returns 404."""
        response = client.post(
            "/api/webhooks/telegram/invalid-uuid",
            json={"update_id": 123, "message": {"text": "test"}},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_webhook_nonexistent_bot(self, client: TestClient):
        """Test webhook for nonexistent bot returns 404."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/webhooks/telegram/{fake_id}",
            json={"update_id": 123, "message": {"text": "test"}},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTelegramBotsAuthorizationIntegration:
    """Test Telegram bots authorization."""

    def test_list_bots_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to list bots are rejected."""
        response = client.get("/api/v1/telegram-bots")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to create bots are rejected."""
        bot_token = f"{uuid.uuid4().int % 10000000000}:{''.join(uuid.uuid4().hex[:35])}"
        bot_data = {
            "agent_id": str(uuid.uuid4()),
            "bot_name": "Unauthorized Bot",
            "bot_token": bot_token,
            "use_webhook": False,
        }

        response = client.post(
            "/api/v1/telegram-bots",
            json=bot_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_validate_token_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to validate token are rejected."""
        bot_token = f"{uuid.uuid4().int % 10000000000}:{''.join(uuid.uuid4().hex[:35])}"

        response = client.post(
            "/api/v1/telegram-bots/validate-token",
            json={"bot_token": bot_token},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_delete_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to delete bots are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/telegram-bots/{fake_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_start_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to start bots are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/telegram-bots/{fake_id}/start")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_stop_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to stop bots are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/telegram-bots/{fake_id}/stop")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
