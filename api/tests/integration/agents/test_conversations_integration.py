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
    from src.models import Account, AccountStatus

    # Create user and get token
    email = f"test_conv_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Conversation Test User",
            "tenant_name": "Conversation Test Org",
        },
    )
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
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account_id


class TestConversationsIntegration:
    @pytest.mark.asyncio
    async def test_conversation_lifecycle(
        self, async_client: AsyncClient, async_db_session: AsyncSession, auth_headers
    ):
        headers, tenant_id, account_id = auth_headers

        # 1. Create Agent
        agent = Agent(
            agent_name=f"ConvAgent_{uuid.uuid4().hex[:8]}",
            tenant_id=uuid.UUID(tenant_id),
            description="Agent for Conversation Tests",
            system_prompt="You are a bot.",
            agent_type="llm",
            llm_config={"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "sk-test-key", "temperature": 0.7},
            is_public=False,
            status="ACTIVE",
        )
        async_db_session.add(agent)
        await async_db_session.commit()
        await async_db_session.refresh(agent)

        # 2. Create Conversation
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        response = await async_client.post(
            "/api/v1/agents/conversations",
            json={"agent_id": str(agent.id), "session_id": session_id, "name": "Test Conversation 1"},
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        conversation_id = data["data"]["id"]
        assert data["data"]["session_id"] == session_id

        # 3. Get Conversation
        response = await async_client.get(f"/api/v1/agents/conversations/{conversation_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == conversation_id
        assert data["data"]["name"] == "Test Conversation 1"

        # 4. List Conversations
        response = await async_client.get(f"/api/v1/agents/{agent.id}/conversations", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["conversations"]) >= 1
        ids = [c["id"] for c in data["data"]["conversations"]]
        assert conversation_id in ids

        # 5. Update Conversation
        response = await async_client.put(
            f"/api/v1/agents/conversations/{conversation_id}",
            json={"name": "Updated Name", "summary": "Updated Summary"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["name"] == "Updated Name"

        # 6. Delete Conversation
        response = await async_client.delete(f"/api/v1/agents/conversations/{conversation_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Verify Deletion (Soft Delete usually)
        # The endpoint returns success. The service returns the conversation even if soft deleted.
        response = await async_client.get(f"/api/v1/agents/conversations/{conversation_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"] == "DELETED"
