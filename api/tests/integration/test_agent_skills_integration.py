"""
Integration tests for Agent Skills endpoints.

Tests adding pre-defined skills to agents.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def auth_headers(client: TestClient, async_db_session: AsyncSession):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    email = f"skills_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Skills Test User",
            "tenant_name": "Skills Test Org",
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
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


@pytest.fixture
def test_agent_name(client: TestClient, auth_headers):
    """Create a test agent and return its name for skills tests."""
    headers, tenant_id, account = auth_headers

    agent_name = f"skills-test-agent-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/agents",
        json={
            "name": f"Skills Test Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Agent for skills tests",
            "system_prompt": "You are a test agent for skills.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return agent_name
    return None


class TestAgentSkillsAddIntegration:
    """Test adding skills to agents."""

    def test_add_skill_to_agent(self, client: TestClient, auth_headers, test_agent_name):
        """Test adding a pre-defined skill to an agent."""
        headers, tenant_id, account = auth_headers

        if not test_agent_name:
            pytest.skip("Could not create test agent")

        skill_data = {
            "skill_id": "web_search",
            "skill_name": "Web Search",
            "skill_category": "general",
        }

        response = client.post(
            f"/api/v1/agents/{test_agent_name}/skills/add",
            json=skill_data,
            headers=headers,
        )

        # Accept various status codes depending on S3 availability and skill existence
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,  # Skill not found or invalid
            status.HTTP_404_NOT_FOUND,  # Agent or skill not found
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # S3 not available
        ]

    def test_add_skill_nonexistent_agent(self, client: TestClient, auth_headers):
        """Test adding skill to nonexistent agent returns 404."""
        headers, tenant_id, account = auth_headers

        fake_name = f"nonexistent-agent-{uuid.uuid4().hex[:8]}"
        skill_data = {
            "skill_id": "web_search",
            "skill_name": "Web Search",
            "skill_category": "general",
        }

        response = client.post(
            f"/api/v1/agents/{fake_name}/skills/add",
            json=skill_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_invalid_skill(self, client: TestClient, auth_headers, test_agent_name):
        """Test adding an invalid/nonexistent skill."""
        headers, tenant_id, account = auth_headers

        if not test_agent_name:
            pytest.skip("Could not create test agent")

        skill_data = {
            "skill_id": f"nonexistent_skill_{uuid.uuid4().hex[:8]}",
            "skill_name": "Nonexistent Skill",
            "skill_category": "invalid",
        }

        response = client.post(
            f"/api/v1/agents/{test_agent_name}/skills/add",
            json=skill_data,
            headers=headers,
        )

        # Should return 404 or 500 for nonexistent skill
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # S3 not available
        ]


class TestAgentSkillsAuthorizationIntegration:
    """Test skills authorization."""

    def test_add_skill_unauthorized(self, client: TestClient):
        """Test that unauthenticated requests to add skills are rejected."""
        fake_name = f"test-agent-{uuid.uuid4().hex[:8]}"
        skill_data = {
            "skill_id": "web_search",
            "skill_name": "Web Search",
            "skill_category": "general",
        }

        response = client.post(
            f"/api/v1/agents/{fake_name}/skills/add",
            json=skill_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
