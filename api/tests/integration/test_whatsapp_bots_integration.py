"""
Integration tests for WhatsApp Bots endpoints.

Tests WhatsApp bot CRUD operations.
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

    email = f"whatsapp_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "WhatsApp Test User",
            "tenant_name": "WhatsApp Test Org",
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
    """Create a test agent for WhatsApp bot tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"whatsapp-test-agent-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/agents",
        json={
            "name": f"WhatsApp Test Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Agent for WhatsApp bot tests",
            "system_prompt": "You are a test agent for WhatsApp.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return response.json()["id"]
    return None


class TestWhatsAppBotsListIntegration:
    """Test listing WhatsApp bots."""

    def test_list_whatsapp_bots(self, client: TestClient, auth_headers):
        """Test listing all WhatsApp bots."""
        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/whatsapp-bots",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "bots" in data["data"]
        assert isinstance(data["data"]["bots"], list)

    def test_list_whatsapp_bots_filter_by_agent(self, client: TestClient, auth_headers, test_agent):
        """Test listing WhatsApp bots filtered by agent."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        response = client.get(
            f"/api/v1/whatsapp-bots?agent_id={test_agent}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_list_whatsapp_bots_invalid_agent_id(self, client: TestClient, auth_headers):
        """Test listing WhatsApp bots with invalid agent ID format."""
        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/whatsapp-bots?agent_id=invalid-uuid",
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWhatsAppBotsCRUDIntegration:
    """Test WhatsApp bot CRUD operations."""

    def test_create_whatsapp_bot(self, client: TestClient, auth_headers, test_agent):
        """Test creating a WhatsApp bot."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Test WhatsApp Bot {uuid.uuid4().hex[:8]}",
            "phone_number_id": f"phone-{uuid.uuid4().hex[:8]}",
            "business_account_id": f"business-{uuid.uuid4().hex[:8]}",
            "access_token": f"token-{uuid.uuid4().hex}",
            "verify_token": f"verify-{uuid.uuid4().hex[:16]}",
            "webhook_url": "https://example.com/whatsapp/webhook",
        }

        response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == bot_data["bot_name"]
        assert data["data"]["agent_id"] == test_agent
        assert "bot_id" in data["data"]

    def test_create_whatsapp_bot_nonexistent_agent(self, client: TestClient, auth_headers):
        """Test creating a WhatsApp bot for nonexistent agent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_agent_id = str(uuid.uuid4())
        bot_data = {
            "agent_id": fake_agent_id,
            "bot_name": "Should Fail Bot",
            "phone_number_id": "phone-123",
            "business_account_id": "business-123",
            "access_token": "token-123",
            "verify_token": "verify-123",
        }

        response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_whatsapp_bot_invalid_agent_id(self, client: TestClient, auth_headers):
        """Test creating a WhatsApp bot with invalid agent ID format."""
        headers, tenant_id, account = auth_headers

        bot_data = {
            "agent_id": "invalid-uuid",
            "bot_name": "Should Fail Bot",
            "phone_number_id": "phone-123",
            "business_account_id": "business-123",
            "access_token": "token-123",
            "verify_token": "verify-123",
        }

        response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_whatsapp_bot(self, client: TestClient, auth_headers, test_agent):
        """Test getting a specific WhatsApp bot."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Get Test Bot {uuid.uuid4().hex[:8]}",
            "phone_number_id": f"phone-{uuid.uuid4().hex[:8]}",
            "business_account_id": f"business-{uuid.uuid4().hex[:8]}",
            "access_token": "test-token",
            "verify_token": "test-verify",
        }

        create_response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create WhatsApp bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Now get the bot
        response = client.get(
            f"/api/v1/whatsapp-bots/{bot_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == bot_data["bot_name"]

    def test_get_whatsapp_bot_not_found(self, client: TestClient, auth_headers):
        """Test getting a nonexistent WhatsApp bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/whatsapp-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_whatsapp_bot_invalid_id(self, client: TestClient, auth_headers):
        """Test getting a WhatsApp bot with invalid ID format."""
        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/whatsapp-bots/invalid-uuid",
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_whatsapp_bot(self, client: TestClient, auth_headers, test_agent):
        """Test updating a WhatsApp bot."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Update Test Bot {uuid.uuid4().hex[:8]}",
            "phone_number_id": f"phone-{uuid.uuid4().hex[:8]}",
            "business_account_id": f"business-{uuid.uuid4().hex[:8]}",
            "access_token": "original-token",
            "verify_token": "original-verify",
        }

        create_response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create WhatsApp bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Update the bot
        update_data = {
            "bot_name": f"Updated Bot {uuid.uuid4().hex[:8]}",
            "is_active": False,
        }

        response = client.put(
            f"/api/v1/whatsapp-bots/{bot_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == update_data["bot_name"]
        assert data["data"]["is_active"] is False

    def test_update_whatsapp_bot_not_found(self, client: TestClient, auth_headers):
        """Test updating a nonexistent WhatsApp bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        update_data = {"bot_name": "Should Fail"}

        response = client.put(
            f"/api/v1/whatsapp-bots/{fake_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_whatsapp_bot(self, client: TestClient, auth_headers, test_agent):
        """Test deleting a WhatsApp bot."""
        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Delete Test Bot {uuid.uuid4().hex[:8]}",
            "phone_number_id": f"phone-{uuid.uuid4().hex[:8]}",
            "business_account_id": f"business-{uuid.uuid4().hex[:8]}",
            "access_token": "to-be-deleted",
            "verify_token": "to-be-deleted",
        }

        create_response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create WhatsApp bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Delete the bot
        response = client.delete(
            f"/api/v1/whatsapp-bots/{bot_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/whatsapp-bots/{bot_id}",
            headers=headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_whatsapp_bot_not_found(self, client: TestClient, auth_headers):
        """Test deleting a nonexistent WhatsApp bot returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/whatsapp-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWhatsAppBotsWebhookIntegration:
    """Test WhatsApp bot webhook endpoints."""

    def test_webhook_verify_invalid_bot_id(self, client: TestClient):
        """Test webhook verification with invalid bot ID returns error."""
        response = client.get(
            "/api/v1/whatsapp-bots/invalid-uuid/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "12345",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_post_invalid_bot_id(self, client: TestClient):
        """Test webhook POST with invalid bot ID returns error."""
        response = client.post(
            "/api/v1/whatsapp-bots/invalid-uuid/webhook",
            json={"entry": [{"changes": []}]},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_post_nonexistent_bot(self, client: TestClient):
        """Test webhook POST for nonexistent bot returns ok (to prevent retries)."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/whatsapp-bots/{fake_id}/webhook",
            json={"entry": [{"changes": []}]},
        )

        # Webhook returns ok or error status but not HTTP error (to prevent retries)
        assert response.status_code == status.HTTP_200_OK


class TestWhatsAppBotsAuthorizationIntegration:
    """Test WhatsApp bots authorization."""

    def test_list_bots_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to list bots are rejected."""
        response = client.get("/api/v1/whatsapp-bots")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to create bots are rejected."""
        bot_data = {
            "agent_id": str(uuid.uuid4()),
            "bot_name": "Unauthorized Bot",
            "phone_number_id": "phone-123",
            "business_account_id": "business-123",
            "access_token": "token-123",
            "verify_token": "verify-123",
        }

        response = client.post(
            "/api/v1/whatsapp-bots",
            json=bot_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to get bot details are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/whatsapp-bots/{fake_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_update_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to update bots are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/whatsapp-bots/{fake_id}",
            json={"bot_name": "Should Fail"},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_delete_bot_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to delete bots are rejected."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/whatsapp-bots/{fake_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
