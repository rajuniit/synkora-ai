"""
Integration tests for Agent Tools CRUD operations.

Tests the complete lifecycle of agent tools: list, add, update, delete, capabilities.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, async_db_session: AsyncSession):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    # Create user and get token
    email = f"test_agent_tools_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Agent Tools Test User",
            "tenant_name": "Agent Tools Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]
    account_id = data["data"]["account"]["id"]

    # Manually activate account for testing (simulating email verification)
    result = await async_db_session.execute(select(Account).filter_by(email=email))
    account = result.scalar_one()
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


@pytest_asyncio.fixture
async def test_agent(async_db_session: AsyncSession, auth_headers):
    """Create a test agent for tools tests."""
    headers, tenant_id, account_id = auth_headers

    agent = Agent(
        agent_name=f"ToolsAgent_{uuid.uuid4().hex[:8]}",
        tenant_id=uuid.UUID(tenant_id),
        description="Agent for tools tests",
        system_prompt="You are a helpful assistant.",
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
    await async_db_session.commit()
    await async_db_session.refresh(agent)
    return agent


class TestAgentToolsListIntegration:
    """Test listing available tools."""

    @pytest.mark.asyncio
    async def test_list_available_tools(self, async_client: AsyncClient, auth_headers):
        """Test listing all available tools."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.get("/api/v1/agents/tools", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "tools" in data["data"]
        assert isinstance(data["data"]["tools"], list)

    @pytest.mark.asyncio
    async def test_list_agent_tools_empty(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test listing tools for agent with no tools configured."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.get(f"/api/v1/agents/{test_agent.id}/tools", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["tools"] == []


class TestAgentToolsCRUDIntegration:
    """Test Agent Tools CRUD operations."""

    @pytest.mark.asyncio
    async def test_agent_tool_lifecycle(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test complete agent tool lifecycle: add -> list -> update -> delete."""
        headers, tenant_id, account_id = auth_headers
        tool_name = "internal_read_file"

        # 1. Add Tool to Agent
        add_response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/tools",
            json={
                "tool_name": tool_name,
                "config": {},
                "enabled": True,
            },
            headers=headers,
        )

        assert add_response.status_code == status.HTTP_200_OK
        add_data = add_response.json()
        assert add_data["success"] is True
        assert add_data["data"]["tool_name"] == tool_name

        # 2. List Agent Tools
        list_response = await async_client.get(f"/api/v1/agents/{test_agent.id}/tools", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert len(list_data["data"]["tools"]) >= 1
        tool_names = [t["tool_name"] for t in list_data["data"]["tools"]]
        assert tool_name in tool_names

        # Get tool ID for deletion
        tool_id = None
        for tool in list_data["data"]["tools"]:
            if tool["tool_name"] == tool_name:
                tool_id = tool["id"]
                break

        # 3. Update Tool (disable it)
        update_response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/tools",
            json={
                "tool_name": tool_name,
                "config": {"some_setting": "value"},
                "enabled": False,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["data"]["enabled"] is False

        # 4. Delete Tool
        delete_response = await async_client.delete(f"/api/v1/agents/{test_agent.id}/tools/{tool_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_200_OK
        assert delete_response.json()["success"] is True

        # Verify deletion
        verify_response = await async_client.get(f"/api/v1/agents/{test_agent.id}/tools", headers=headers)
        verify_data = verify_response.json()
        tool_names = [t["tool_name"] for t in verify_data["data"]["tools"]]
        assert tool_name not in tool_names

    @pytest.mark.asyncio
    async def test_add_tool_to_nonexistent_agent(self, async_client: AsyncClient, auth_headers):
        """Test that adding a tool to a nonexistent agent returns 404."""
        headers, tenant_id, account_id = auth_headers
        fake_id = str(uuid.uuid4())

        response = await async_client.post(
            f"/api/v1/agents/{fake_id}/tools",
            json={
                "tool_name": "test_tool",
                "config": {},
                "enabled": True,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tool(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test that deleting a nonexistent tool returns 404."""
        headers, tenant_id, account_id = auth_headers
        fake_tool_id = str(uuid.uuid4())

        response = await async_client.delete(f"/api/v1/agents/{test_agent.id}/tools/{fake_tool_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_add_internal_tool(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test adding an internal tool."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/tools",
            json={
                "tool_name": "internal_write_file",
                "config": {},
                "enabled": True,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK


class TestAgentToolTestIntegration:
    """Test Agent Tool testing endpoints."""

    @pytest.mark.asyncio
    async def test_tool_internal_tool_test(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test testing an internal tool configuration."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/tools/internal_read_file/test",
            json={"config": {}},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True

    @pytest.mark.asyncio
    async def test_tool_test_missing_required_config(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test that testing a tool with missing required config fails."""
        headers, tenant_id, account_id = auth_headers

        # web_search requires SERPAPI_KEY
        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/tools/web_search/test",
            json={"config": {}},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAgentCapabilitiesIntegration:
    """Test Agent Capabilities operations."""

    @pytest.mark.asyncio
    async def test_list_capabilities(self, async_client: AsyncClient, auth_headers):
        """Test listing all capabilities."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.get("/api/v1/agents/capabilities", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "capabilities" in data["data"]
        assert len(data["data"]["capabilities"]) > 0

        # Verify capability structure
        capability = data["data"]["capabilities"][0]
        assert "id" in capability
        assert "name" in capability
        assert "description" in capability
        assert "tools" in capability
        assert "tool_count" in capability

    @pytest.mark.asyncio
    async def test_enable_capability(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test enabling a capability on an agent."""
        headers, tenant_id, account_id = auth_headers

        # Enable files-storage capability
        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/capabilities/files-storage",
            json={},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "enabled_tools" in data["data"]

    @pytest.mark.asyncio
    async def test_disable_capability(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test disabling a capability on an agent."""
        headers, tenant_id, account_id = auth_headers

        # First enable a capability
        await async_client.post(
            f"/api/v1/agents/{test_agent.id}/capabilities/files-storage",
            json={},
            headers=headers,
        )

        # Then disable it
        response = await async_client.delete(f"/api/v1/agents/{test_agent.id}/capabilities/files-storage", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "disabled_tools" in data["data"]

    @pytest.mark.asyncio
    async def test_enable_nonexistent_capability(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test that enabling a nonexistent capability returns 404."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/capabilities/nonexistent-capability",
            json={},
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_enable_capabilities_bulk(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test enabling multiple capabilities at once."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/capabilities/bulk",
            json={
                "capability_ids": ["files-storage", "database-analytics"],
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "total_tools_enabled" in data["data"]
        assert data["data"]["total_tools_enabled"] > 0

    @pytest.mark.asyncio
    async def test_enable_capabilities_bulk_with_invalid(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test that bulk enable with invalid capability ID fails."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            f"/api/v1/agents/{test_agent.id}/capabilities/bulk",
            json={
                "capability_ids": ["files-storage", "invalid-capability"],
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAgentToolsTenantIsolation:
    """Test Agent Tools tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_agent_tools(self, async_client: AsyncClient, async_db_session: AsyncSession):
        """Test that users cannot access tools for agents from other tenants."""
        from src.models import Account, AccountStatus

        # Create first user/tenant
        email1 = f"tenant1_tools_{uuid.uuid4()}@example.com"
        response1 = await async_client.post(
            "/console/api/auth/register",
            json={
                "email": email1,
                "password": "SecureTestPass123!",
                "name": "Tenant 1 User",
                "tenant_name": "Tenant 1 Org",
            },
        )
        tenant1_id = response1.json()["data"]["tenant"]["id"]
        result1 = await async_db_session.execute(select(Account).filter_by(email=email1))
        account1 = result1.scalar_one()
        account1.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        login1 = await async_client.post("/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"})
        login1.json()["data"]["access_token"]

        # Create agent for tenant 1
        agent1 = Agent(
            agent_name=f"Tenant1ToolsAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant1_id),
            description="Tenant 1 agent",
            system_prompt="You are a helpful assistant.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test"},
            status="ACTIVE",
        )
        async_db_session.add(agent1)
        await async_db_session.commit()
        await async_db_session.refresh(agent1)

        # Create second user/tenant
        email2 = f"tenant2_tools_{uuid.uuid4()}@example.com"
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
        account2 = result2.scalar_one()
        account2.status = AccountStatus.ACTIVE
        await async_db_session.commit()

        login2 = await async_client.post("/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"})
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Tenant 2 should not be able to add tools to tenant 1's agent
        add_response = await async_client.post(
            f"/api/v1/agents/{agent1.id}/tools",
            json={
                "tool_name": "internal_read_file",
                "config": {},
                "enabled": True,
            },
            headers=headers2,
        )
        assert add_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to enable capabilities on tenant 1's agent
        cap_response = await async_client.post(
            f"/api/v1/agents/{agent1.id}/capabilities/files-storage",
            json={},
            headers=headers2,
        )
        assert cap_response.status_code == status.HTTP_404_NOT_FOUND
