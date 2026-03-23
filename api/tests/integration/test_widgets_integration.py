"""
Integration tests for Widgets CRUD operations.

Tests the complete lifecycle of widgets: create, list, get, update, delete.
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
    email = f"test_widgets_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = await async_client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Widgets Test User",
            "tenant_name": "Widgets Test Org",
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
    """Create a test agent for widget tests."""
    headers, tenant_id, account_id = auth_headers

    agent = Agent(
        agent_name=f"WidgetAgent_{uuid.uuid4().hex[:8]}",
        tenant_id=uuid.UUID(tenant_id),
        description="Agent for widget tests",
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


class TestWidgetsCRUDIntegration:
    """Test Widgets CRUD operations."""

    @pytest.mark.asyncio
    async def test_widget_full_lifecycle(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test complete widget lifecycle: create -> get -> update -> delete."""
        headers, tenant_id, account_id = auth_headers
        widget_name = f"TestWidget_{uuid.uuid4().hex[:8]}"

        # 1. Create Widget
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(test_agent.id),
                "widget_name": widget_name,
                "allowed_domains": ["https://example.com", "https://app.example.com"],
                "theme_config": {"primaryColor": "#007bff", "position": "bottom-right"},
                "rate_limit": 100,
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        create_data = create_response.json()
        assert create_data["success"] is True
        assert create_data["data"]["widget_name"] == widget_name
        assert "api_key" in create_data["data"]
        assert create_data["data"]["api_key"].startswith("widget_")
        widget_id = create_data["data"]["widget_id"]

        # 2. Get Widget
        get_response = await async_client.get(f"/api/v1/widgets/{widget_id}", headers=headers)
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["success"] is True
        assert get_data["data"]["widget_name"] == widget_name
        assert get_data["data"]["rate_limit"] == 100

        # 3. List Widgets
        list_response = await async_client.get("/api/v1/widgets", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert list_data["success"] is True
        widget_ids = [w["widget_id"] for w in list_data["data"]["widgets"]]
        assert widget_id in widget_ids

        # 4. Update Widget
        update_response = await async_client.put(
            f"/api/v1/widgets/{widget_id}",
            json={
                "widget_name": f"{widget_name}_updated",
                "rate_limit": 200,
                "is_active": False,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["data"]["widget_name"] == f"{widget_name}_updated"
        assert update_data["data"]["rate_limit"] == 200
        assert update_data["data"]["is_active"] is False

        # 5. Get Embed Code
        embed_response = await async_client.get(f"/api/v1/widgets/{widget_id}/embed-code", headers=headers)
        assert embed_response.status_code == status.HTTP_200_OK
        embed_data = embed_response.json()
        assert "embed_code" in embed_data["data"]
        assert widget_id in embed_data["data"]["embed_code"]

        # 6. Delete Widget
        delete_response = await async_client.delete(f"/api/v1/widgets/{widget_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_200_OK
        assert delete_response.json()["success"] is True

        # Verify deletion
        verify_response = await async_client.get(f"/api/v1/widgets/{widget_id}", headers=headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_widget_for_nonexistent_agent(self, async_client: AsyncClient, auth_headers):
        """Test that creating a widget for a nonexistent agent fails."""
        headers, tenant_id, account_id = auth_headers
        fake_agent_id = str(uuid.uuid4())

        response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": fake_agent_id,
                "widget_name": "TestWidget",
                "rate_limit": 100,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_widget_with_invalid_agent_id(self, async_client: AsyncClient, auth_headers):
        """Test that creating a widget with invalid agent ID format fails."""
        headers, tenant_id, account_id = auth_headers

        response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": "invalid-uuid",
                "widget_name": "TestWidget",
                "rate_limit": 100,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_nonexistent_widget(self, async_client: AsyncClient, auth_headers):
        """Test that getting a nonexistent widget returns 404."""
        headers, tenant_id, account_id = auth_headers
        fake_id = str(uuid.uuid4())

        response = await async_client.get(f"/api/v1/widgets/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_widgets_by_agent(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test listing widgets filtered by agent ID."""
        headers, tenant_id, account_id = auth_headers

        # Create widgets for the test agent
        for i in range(3):
            await async_client.post(
                "/api/v1/widgets",
                json={
                    "agent_id": str(test_agent.id),
                    "widget_name": f"AgentWidget_{uuid.uuid4().hex[:8]}_{i}",
                    "rate_limit": 100,
                },
                headers=headers,
            )

        # List widgets filtered by agent
        response = await async_client.get(f"/api/v1/widgets?agent_id={test_agent.id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["widgets"]) >= 3

    @pytest.mark.asyncio
    async def test_regenerate_widget_api_key(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test regenerating widget API key."""
        headers, tenant_id, account_id = auth_headers

        # Create widget
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(test_agent.id),
                "widget_name": f"RegenerateKeyWidget_{uuid.uuid4().hex[:8]}",
                "rate_limit": 100,
            },
            headers=headers,
        )
        widget_id = create_response.json()["data"]["widget_id"]
        original_key = create_response.json()["data"]["api_key"]

        # Regenerate API key
        regenerate_response = await async_client.post(f"/api/v1/widgets/{widget_id}/regenerate-key", headers=headers)
        assert regenerate_response.status_code == status.HTTP_200_OK
        new_key = regenerate_response.json()["data"]["api_key"]

        # Verify key changed
        assert new_key != original_key
        assert new_key.startswith("widget_")

    @pytest.mark.asyncio
    async def test_widget_analytics(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test getting widget analytics."""
        headers, tenant_id, account_id = auth_headers

        # Create widget
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(test_agent.id),
                "widget_name": f"AnalyticsWidget_{uuid.uuid4().hex[:8]}",
                "rate_limit": 100,
            },
            headers=headers,
        )
        widget_id = create_response.json()["data"]["widget_id"]

        # Get analytics (should be empty initially)
        analytics_response = await async_client.get(f"/api/v1/widgets/{widget_id}/analytics", headers=headers)
        assert analytics_response.status_code == status.HTTP_200_OK
        analytics_data = analytics_response.json()
        assert analytics_data["success"] is True
        assert "summary" in analytics_data["data"]
        assert analytics_data["data"]["summary"]["total_sessions"] == 0

    @pytest.mark.asyncio
    async def test_update_widget_domains(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test updating widget allowed domains."""
        headers, tenant_id, account_id = auth_headers

        # Create widget
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(test_agent.id),
                "widget_name": f"DomainsWidget_{uuid.uuid4().hex[:8]}",
                "allowed_domains": ["https://example.com"],
                "rate_limit": 100,
            },
            headers=headers,
        )
        widget_id = create_response.json()["data"]["widget_id"]

        # Update domains
        update_response = await async_client.put(
            f"/api/v1/widgets/{widget_id}",
            json={
                "allowed_domains": ["https://newdomain.com", "https://another.com"],
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert "https://newdomain.com" in update_data["data"]["allowed_domains"]

    @pytest.mark.asyncio
    async def test_update_widget_theme_config(self, async_client: AsyncClient, auth_headers, test_agent):
        """Test updating widget theme configuration."""
        headers, tenant_id, account_id = auth_headers

        # Create widget
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(test_agent.id),
                "widget_name": f"ThemeWidget_{uuid.uuid4().hex[:8]}",
                "theme_config": {"primaryColor": "#000000"},
                "rate_limit": 100,
            },
            headers=headers,
        )
        widget_id = create_response.json()["data"]["widget_id"]

        # Update theme
        update_response = await async_client.put(
            f"/api/v1/widgets/{widget_id}",
            json={
                "theme_config": {
                    "primaryColor": "#ff0000",
                    "position": "bottom-left",
                    "greeting": "Hello! How can I help you?",
                },
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["data"]["theme_config"]["primaryColor"] == "#ff0000"


class TestWidgetsTenantIsolation:
    """Test Widgets tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_widget(self, async_client: AsyncClient, async_db_session: AsyncSession):
        """Test that users cannot access widgets from other tenants."""
        from src.models import Account, AccountStatus

        # Create first user/tenant
        email1 = f"tenant1_widget_{uuid.uuid4()}@example.com"
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

        login1 = await async_client.post(
            "/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"}
        )
        token1 = login1.json()["data"]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create agent for tenant 1
        agent1 = Agent(
            agent_name=f"Tenant1Agent_{uuid.uuid4().hex[:8]}",
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
        email2 = f"tenant2_widget_{uuid.uuid4()}@example.com"
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

        login2 = await async_client.post(
            "/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"}
        )
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Create widget as tenant 1
        create_response = await async_client.post(
            "/api/v1/widgets",
            json={
                "agent_id": str(agent1.id),
                "widget_name": f"IsolatedWidget_{uuid.uuid4().hex[:8]}",
                "rate_limit": 100,
            },
            headers=headers1,
        )
        widget_id = create_response.json()["data"]["widget_id"]

        # Tenant 2 should not be able to access tenant 1's widget
        get_response = await async_client.get(f"/api/v1/widgets/{widget_id}", headers=headers2)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to update tenant 1's widget
        update_response = await async_client.put(
            f"/api/v1/widgets/{widget_id}", json={"widget_name": "Hacked Widget"}, headers=headers2
        )
        assert update_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to delete tenant 1's widget
        delete_response = await async_client.delete(f"/api/v1/widgets/{widget_id}", headers=headers2)
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
