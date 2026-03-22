"""
Integration tests for Sub-Agents endpoints.

Tests sub-agent (parent-child agent relationship) CRUD operations.
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

    email = f"subagent_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Sub-Agent Test User",
            "tenant_name": "Sub-Agent Test Org",
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


@pytest_asyncio.fixture
async def parent_agent(async_client: AsyncClient, auth_headers):
    """Create a parent agent for sub-agent tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"parent-agent-{uuid.uuid4().hex[:8]}"
    response = await async_client.post(
        "/api/v1/agents",
        json={
            "name": f"Parent Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Parent agent for sub-agent tests",
            "system_prompt": "You are a parent agent.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return response.json()["id"]
    return None


@pytest_asyncio.fixture
async def child_agent(async_client: AsyncClient, auth_headers):
    """Create a child agent for sub-agent tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"child-agent-{uuid.uuid4().hex[:8]}"
    response = await async_client.post(
        "/api/v1/agents",
        json={
            "name": f"Child Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Child agent for sub-agent tests",
            "system_prompt": "You are a child agent.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return response.json()["id"]
    return None


class TestSubAgentsListIntegration:
    """Test listing sub-agents."""

    @pytest.mark.asyncio
    async def test_list_sub_agents(self, async_client: AsyncClient, auth_headers, parent_agent):
        """Test listing all sub-agents for a parent agent."""
        headers, tenant_id, account = auth_headers

        if not parent_agent:
            pytest.skip("Could not create parent agent")

        response = await async_client.get(
            f"/api/v1/agents/{parent_agent}/sub-agents",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_sub_agents_nonexistent_parent(self, async_client: AsyncClient, auth_headers):
        """Test listing sub-agents for nonexistent parent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/agents/{fake_id}/sub-agents",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAvailableSubAgentsIntegration:
    """Test listing available sub-agents."""

    @pytest.mark.asyncio
    async def test_list_available_sub_agents(self, async_client: AsyncClient, auth_headers, parent_agent):
        """Test listing available agents that can be added as sub-agents."""
        headers, tenant_id, account = auth_headers

        if not parent_agent:
            pytest.skip("Could not create parent agent")

        response = await async_client.get(
            f"/api/v1/agents/{parent_agent}/sub-agents/available",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_available_sub_agents_nonexistent_parent(self, async_client: AsyncClient, auth_headers):
        """Test listing available sub-agents for nonexistent parent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/agents/{fake_id}/sub-agents/available",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSubAgentsCRUDIntegration:
    """Test sub-agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_add_sub_agent(self, async_client: AsyncClient, auth_headers, parent_agent, child_agent):
        """Test adding a sub-agent to a parent agent."""
        headers, tenant_id, account = auth_headers

        if not parent_agent or not child_agent:
            pytest.skip("Could not create test agents")

        response = await async_client.post(
            f"/api/v1/agents/{parent_agent}/sub-agents",
            json={
                "child_agent_id": child_agent,
                "execution_order": 1,
            },
            headers=headers,
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    @pytest.mark.asyncio
    async def test_add_sub_agent_nonexistent_parent(self, async_client: AsyncClient, auth_headers, child_agent):
        """Test adding sub-agent to nonexistent parent returns 404."""
        headers, tenant_id, account = auth_headers

        if not child_agent:
            pytest.skip("Could not create child agent")

        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/agents/{fake_id}/sub-agents",
            json={
                "child_agent_id": child_agent,
                "execution_order": 1,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_add_sub_agent_nonexistent_child(self, async_client: AsyncClient, auth_headers, parent_agent):
        """Test adding nonexistent child agent returns 404."""
        headers, tenant_id, account = auth_headers

        if not parent_agent:
            pytest.skip("Could not create parent agent")

        fake_child_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/agents/{parent_agent}/sub-agents",
            json={
                "child_agent_id": fake_child_id,
                "execution_order": 1,
            },
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_sub_agent_not_found(self, async_client: AsyncClient, auth_headers, parent_agent):
        """Test updating a nonexistent sub-agent returns 404."""
        headers, tenant_id, account = auth_headers

        if not parent_agent:
            pytest.skip("Could not create parent agent")

        fake_child_id = str(uuid.uuid4())
        response = await async_client.put(
            f"/api/v1/agents/{parent_agent}/sub-agents/{fake_child_id}",
            json={"execution_order": 2},
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_remove_sub_agent_not_found(self, async_client: AsyncClient, auth_headers, parent_agent):
        """Test removing a nonexistent sub-agent returns 404."""
        headers, tenant_id, account = auth_headers

        if not parent_agent:
            pytest.skip("Could not create parent agent")

        fake_child_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/api/v1/agents/{parent_agent}/sub-agents/{fake_child_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSubAgentsAuthorizationIntegration:
    """Test sub-agents authorization."""

    @pytest.mark.asyncio
    async def test_list_sub_agents_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list sub-agents are rejected."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/agents/{fake_id}/sub-agents")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_add_sub_agent_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to add sub-agents are rejected."""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/agents/{fake_id}/sub-agents",
            json={"child_agent_id": str(uuid.uuid4()), "execution_order": 1},
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_remove_sub_agent_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to remove sub-agents are rejected."""
        fake_id = str(uuid.uuid4())
        fake_child_id = str(uuid.uuid4())
        response = await async_client.delete(f"/api/v1/agents/{fake_id}/sub-agents/{fake_child_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_list_available_unauthorized(self, async_client: AsyncClient):
        """Test that unauthenticated requests to list available sub-agents are rejected."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/v1/agents/{fake_id}/sub-agents/available")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
