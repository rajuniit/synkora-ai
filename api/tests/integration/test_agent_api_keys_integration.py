"""
Integration tests for Agent API Keys CRUD operations.

Tests the complete lifecycle of API keys: create, list, get, update, delete, regenerate.
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

    # Create user and get token
    email = f"test_api_keys_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "API Keys Test User",
            "tenant_name": "API Keys Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]
    account_id = data["data"]["account"]["id"]

    # Manually activate account for testing (simulating email verification)
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one_or_none()
    account.status = AccountStatus.ACTIVE
    await async_db_session.commit()

    # Login to get token
    login_response = await async_client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account_id


class TestAgentApiKeysCRUDIntegration:
    """Test Agent API Keys CRUD operations."""

    @pytest.mark.asyncio
    async def test_api_key_full_lifecycle(
        self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers
    ):
        """Test complete API key lifecycle: create -> get -> update -> delete."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"TestAPIKey_{uuid.uuid4().hex[:8]}"

        # First create an agent to attach the API key to
        agent = Agent(
            agent_name=f"ApiKeyTestAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for API key tests",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # 1. Create API Key (with agent_id to ensure valid reference)
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={
                "key_name": key_name,
                "agent_id": str(agent.id),
                "permissions": ["agent:chat", "agent:read"],
                "rate_limit_per_minute": 60,
                "rate_limit_per_hour": 1000,
                "rate_limit_per_day": 10000,
            },
            headers=headers,
        )

        # Debug: print response if failed
        if create_response.status_code != status.HTTP_200_OK:
            print(f"Create API key failed: {create_response.json()}")

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert create_data["key_name"] == key_name
        assert "api_key" in create_data  # Full key only shown at creation
        key_id = str(create_data["id"])

        # 2. Get API Key
        get_response = await async_client.get(f"/api/v1/agent-api-keys/{key_id}", headers=headers)
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["key_name"] == key_name

        # 3. List API Keys
        list_response = await async_client.get("/api/v1/agent-api-keys", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert list_data["total"] >= 1
        key_ids = [str(k["id"]) for k in list_data["keys"]]
        assert key_id in key_ids

        # 4. Update API Key
        update_response = await async_client.put(
            f"/api/v1/agent-api-keys/{key_id}",
            json={
                "key_name": f"{key_name}_updated",
                "rate_limit_per_minute": 120,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["key_name"] == f"{key_name}_updated"
        assert update_data["rate_limit_per_minute"] == 120

        # 5. Delete API Key
        delete_response = await async_client.delete(f"/api/v1/agent-api-keys/{key_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_200_OK
        assert "deleted" in delete_response.json()["message"].lower()

        # Verify deletion
        verify_response = await async_client.get(f"/api/v1/agent-api-keys/{key_id}", headers=headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_api_key_regenerate(self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers):
        """Test API key regeneration."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"RegenerateKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"RegenKeyAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for regen key test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={"key_name": key_name, "agent_id": str(agent.id), "permissions": ["agent:chat"]},
            headers=headers,
        )
        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        key_id = str(create_data["id"])
        original_key = create_data["api_key"]

        # Regenerate API Key
        regenerate_response = await async_client.post(f"/api/v1/agent-api-keys/{key_id}/regenerate", headers=headers)
        assert regenerate_response.status_code == status.HTTP_200_OK
        regenerate_data = regenerate_response.json()
        new_key = regenerate_data["api_key"]

        # Verify key changed
        assert new_key != original_key

    @pytest.mark.asyncio
    async def test_api_key_with_agent(self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers):
        """Test creating API key associated with specific agent."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers

        # Create agent first
        agent_name = f"APIKeyAgent_{uuid.uuid4().hex[:8]}"
        agent = Agent(
            agent_name=agent_name,
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for API key tests",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "sk-test-key",
                "temperature": 0.7,
            },
            is_public=False,
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key for agent
        key_name = f"AgentAPIKey_{uuid.uuid4().hex[:8]}"
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={
                "key_name": key_name,
                "agent_id": str(agent.id),
                "permissions": ["agent:chat"],
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert str(create_data["agent_id"]) == str(agent.id)

        # List API Keys filtered by agent
        list_response = await async_client.get(f"/api/v1/agent-api-keys?agent_id={agent.id}", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert list_data["total"] >= 1

    @pytest.mark.asyncio
    async def test_api_key_with_ip_restriction(
        self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers
    ):
        """Test creating API key with IP restrictions."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"IPRestrictedKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"IPRestrictAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for IP restrict test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key with IP restriction
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={
                "key_name": key_name,
                "agent_id": str(agent.id),
                "permissions": ["agent:chat"],
                "allowed_ips": ["192.168.1.1", "10.0.0.0/8"],
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert create_data["allowed_ips"] == ["192.168.1.1", "10.0.0.0/8"]

    @pytest.mark.asyncio
    async def test_api_key_with_origin_restriction(
        self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers
    ):
        """Test creating API key with origin restrictions."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"OriginRestrictedKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"OriginRestrictAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for origin restrict test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key with origin restriction
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={
                "key_name": key_name,
                "agent_id": str(agent.id),
                "permissions": ["agent:chat"],
                "allowed_origins": ["https://example.com", "https://app.example.com"],
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert "https://example.com" in create_data["allowed_origins"]

    @pytest.mark.asyncio
    async def test_api_key_with_expiration(
        self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers
    ):
        """Test creating API key with expiration date."""
        from datetime import UTC, datetime, timedelta

        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"ExpiringKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"ExpiringKeyAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for expiring key test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Set expiration to 30 days from now
        expiration = (datetime.now(UTC) + timedelta(days=30)).isoformat()

        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={
                "key_name": key_name,
                "agent_id": str(agent.id),
                "permissions": ["agent:chat"],
                "expires_at": expiration,
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_200_OK
        create_data = create_response.json()
        assert create_data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_api_key_deactivate(self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers):
        """Test deactivating an API key."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"DeactivateKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"DeactivateKeyAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for deactivate key test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={"key_name": key_name, "agent_id": str(agent.id), "permissions": ["agent:chat"]},
            headers=headers,
        )
        assert create_response.status_code == status.HTTP_200_OK
        key_id = str(create_response.json()["id"])

        # Deactivate
        update_response = await async_client.put(
            f"/api/v1/agent-api-keys/{key_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["is_active"] is False

        # Reactivate
        reactivate_response = await async_client.put(
            f"/api/v1/agent-api-keys/{key_id}",
            json={"is_active": True},
            headers=headers,
        )
        assert reactivate_response.status_code == status.HTTP_200_OK
        assert reactivate_response.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_api_key(self, async_client: AsyncClient, auth_headers):
        """Test that getting a nonexistent API key returns 404."""
        headers, tenant_id, account_id = auth_headers
        fake_id = str(uuid.uuid4())

        response = await async_client.get(f"/api/v1/agent-api-keys/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_nonexistent_api_key(self, async_client: AsyncClient, auth_headers):
        """Test that deleting a nonexistent API key returns 404."""
        headers, tenant_id, account_id = auth_headers
        fake_id = str(uuid.uuid4())

        response = await async_client.delete(f"/api/v1/agent-api-keys/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_api_key_usage_stats(self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers):
        """Test getting API key usage statistics."""
        from src.models.agent import Agent

        headers, tenant_id, account_id = auth_headers
        key_name = f"UsageStatsKey_{uuid.uuid4().hex[:8]}"

        # First create an agent
        agent = Agent(
            agent_name=f"UsageStatsAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for usage stats test",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.flush()
        await async_db_session.refresh(agent)
        await async_db_session.commit()

        # Create API Key
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={"key_name": key_name, "agent_id": str(agent.id), "permissions": ["agent:chat"]},
            headers=headers,
        )
        assert create_response.status_code == status.HTTP_200_OK
        key_id = str(create_response.json()["id"])

        # Get usage stats
        usage_response = await async_client.get(f"/api/v1/agent-api-keys/{key_id}/usage?days=30", headers=headers)
        assert usage_response.status_code == status.HTTP_200_OK
        usage_data = usage_response.json()
        assert "overall" in usage_data
        assert "by_endpoint" in usage_data
        assert "total_requests" in usage_data["overall"]


class TestAgentApiKeysTenantIsolation:
    """Test API Keys tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_api_key(
        self, async_client: AsyncClient, async_db_session: AsyncSession
    ):
        """Test that users cannot access API keys from other tenants."""
        from src.models import Account, AccountStatus
        from src.models.agent import Agent

        # Create first user/tenant
        email1 = f"tenant1_api_{uuid.uuid4()}@example.com"
        register1 = await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email1,
                "password": "SecureTestPass123!",
                "name": "Tenant 1 User",
                "tenant_name": "Tenant 1 Org",
            },
        )
        tenant1_id = register1.json()["data"]["tenant"]["id"]
        result1 = await async_db_session.execute(select(Account).filter_by(email=email1))
        account1 = result1.scalar_one_or_none()
        account1.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        login1 = await async_client.post(
            "/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"}
        )
        token1 = login1.json()["data"]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create an agent for tenant 1
        agent1 = Agent(
            agent_name=f"Tenant1IsolationAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant1_id),
            description="Tenant 1 agent",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent1)
        await async_db_session.flush()
        await async_db_session.refresh(agent1)
        await async_db_session.commit()

        # Create second user/tenant
        email2 = f"tenant2_api_{uuid.uuid4()}@example.com"
        await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email2,
                "password": "SecureTestPass123!",
                "name": "Tenant 2 User",
                "tenant_name": "Tenant 2 Org",
            },
        )
        result2 = await async_db_session.execute(select(Account).filter_by(email=email2))
        account2 = result2.scalar_one_or_none()
        account2.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        login2 = await async_client.post(
            "/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"}
        )
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Create API Key as tenant 1
        key_name = f"IsolatedKey_{uuid.uuid4().hex[:8]}"
        create_response = await async_client.post(
            "/api/v1/agent-api-keys",
            json={"key_name": key_name, "agent_id": str(agent1.id), "permissions": ["agent:chat"]},
            headers=headers1,
        )
        assert create_response.status_code == status.HTTP_200_OK
        key_id = str(create_response.json()["id"])

        # Tenant 2 should not be able to access tenant 1's API key
        get_response = await async_client.get(f"/api/v1/agent-api-keys/{key_id}", headers=headers2)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to update tenant 1's API key
        update_response = await async_client.put(
            f"/api/v1/agent-api-keys/{key_id}",
            json={"key_name": "Hacked Key"},
            headers=headers2,
        )
        assert update_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to delete tenant 1's API key
        delete_response = await async_client.delete(f"/api/v1/agent-api-keys/{key_id}", headers=headers2)
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
