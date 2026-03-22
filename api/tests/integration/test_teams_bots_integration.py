"""
Integration tests for Teams Bots endpoints.

Tests Microsoft Teams bot CRUD operations.
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session):
    """Create authenticated user and return headers with tenant info."""
    from src.core.database import get_db
    from src.models import Account, AccountStatus

    client.app.dependency_overrides[get_db] = lambda: db_session

    email = f"teams_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Teams Test User",
            "tenant_name": "Teams Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]

    # Activate account
    account = db_session.query(Account).filter_by(email=email).first()
    account.status = AccountStatus.ACTIVE
    db_session.commit()

    # Login
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account


@pytest.fixture
def test_agent(client: TestClient, db_session: Session, auth_headers):
    """Create a test agent for Teams bot tests."""
    from src.core.database import get_db

    client.app.dependency_overrides[get_db] = lambda: db_session

    headers, tenant_id, account = auth_headers

    agent_name = f"teams-test-agent-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/agents",
        json={
            "name": f"Teams Test Agent {uuid.uuid4().hex[:8]}",
            "agent_name": agent_name,
            "description": "Agent for Teams bot tests",
            "system_prompt": "You are a test agent for Microsoft Teams.",
            "model": "gpt-4o-mini",
        },
        headers=headers,
    )
    if response.status_code == status.HTTP_201_CREATED:
        return response.json()["id"]
    return None


class TestTeamsBotsListIntegration:
    """Test listing Teams bots."""

    def test_list_teams_bots(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing all Teams bots."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/teams-bots",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "bots" in data["data"]
        assert isinstance(data["data"]["bots"], list)

    def test_list_teams_bots_filter_by_agent(self, client: TestClient, db_session: Session, auth_headers, test_agent):
        """Test listing Teams bots filtered by agent."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        response = client.get(
            f"/api/v1/teams-bots?agent_id={test_agent}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_list_teams_bots_invalid_agent_id(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing Teams bots with invalid agent ID format."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/teams-bots?agent_id=invalid-uuid",
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTeamsBotsCRUDIntegration:
    """Test Teams bot CRUD operations."""

    def test_create_teams_bot(self, client: TestClient, db_session: Session, auth_headers, test_agent):
        """Test creating a Teams bot."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Test Teams Bot {uuid.uuid4().hex[:8]}",
            "app_id": f"app-{uuid.uuid4().hex[:8]}",
            "app_password": "test-app-password-12345",
            "bot_id": f"bot-{uuid.uuid4().hex[:8]}",
            "webhook_url": "https://example.com/teams/webhook",
            "welcome_message": "Hello from Teams bot!",
        }

        response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == bot_data["bot_name"]
        assert data["data"]["agent_id"] == test_agent
        assert "bot_id" in data["data"]

    def test_create_teams_bot_nonexistent_agent(self, client: TestClient, db_session: Session, auth_headers):
        """Test creating a Teams bot for nonexistent agent returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        fake_agent_id = str(uuid.uuid4())
        bot_data = {
            "agent_id": fake_agent_id,
            "bot_name": "Should Fail Bot",
            "app_id": "app-123",
            "app_password": "password",
            "bot_id": "bot-123",
        }

        response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_teams_bot_invalid_agent_id(self, client: TestClient, db_session: Session, auth_headers):
        """Test creating a Teams bot with invalid agent ID format."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        bot_data = {
            "agent_id": "invalid-uuid",
            "bot_name": "Should Fail Bot",
            "app_id": "app-123",
            "app_password": "password",
            "bot_id": "bot-123",
        }

        response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_teams_bot(self, client: TestClient, db_session: Session, auth_headers, test_agent):
        """Test getting a specific Teams bot."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Get Test Bot {uuid.uuid4().hex[:8]}",
            "app_id": f"app-{uuid.uuid4().hex[:8]}",
            "app_password": "test-password",
            "bot_id": f"bot-{uuid.uuid4().hex[:8]}",
        }

        create_response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create Teams bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Now get the bot
        response = client.get(
            f"/api/v1/teams-bots/{bot_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == bot_data["bot_name"]

    def test_get_teams_bot_not_found(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting a nonexistent Teams bot returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/teams-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_teams_bot_invalid_id(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting a Teams bot with invalid ID format."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        response = client.get(
            "/api/v1/teams-bots/invalid-uuid",
            headers=headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_teams_bot(self, client: TestClient, db_session: Session, auth_headers, test_agent):
        """Test updating a Teams bot."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Update Test Bot {uuid.uuid4().hex[:8]}",
            "app_id": f"app-{uuid.uuid4().hex[:8]}",
            "app_password": "original-password",
            "bot_id": f"bot-{uuid.uuid4().hex[:8]}",
        }

        create_response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create Teams bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Update the bot
        update_data = {
            "bot_name": f"Updated Bot {uuid.uuid4().hex[:8]}",
            "welcome_message": "Updated welcome message",
            "is_active": False,
        }

        response = client.put(
            f"/api/v1/teams-bots/{bot_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == update_data["bot_name"]
        assert data["data"]["is_active"] is False

    def test_update_teams_bot_not_found(self, client: TestClient, db_session: Session, auth_headers):
        """Test updating a nonexistent Teams bot returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        update_data = {"bot_name": "Should Fail"}

        response = client.put(
            f"/api/v1/teams-bots/{fake_id}",
            json=update_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_teams_bot(self, client: TestClient, db_session: Session, auth_headers, test_agent):
        """Test deleting a Teams bot."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        if not test_agent:
            pytest.skip("Could not create test agent")

        # First create a bot
        bot_data = {
            "agent_id": test_agent,
            "bot_name": f"Delete Test Bot {uuid.uuid4().hex[:8]}",
            "app_id": f"app-{uuid.uuid4().hex[:8]}",
            "app_password": "to-be-deleted",
            "bot_id": f"bot-{uuid.uuid4().hex[:8]}",
        }

        create_response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
            headers=headers,
        )

        if create_response.status_code != status.HTTP_201_CREATED:
            pytest.skip("Could not create Teams bot")

        bot_id = create_response.json()["data"]["bot_id"]

        # Delete the bot
        response = client.delete(
            f"/api/v1/teams-bots/{bot_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/teams-bots/{bot_id}",
            headers=headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_teams_bot_not_found(self, client: TestClient, db_session: Session, auth_headers):
        """Test deleting a nonexistent Teams bot returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account = auth_headers

        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/teams-bots/{fake_id}",
            headers=headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeamsBotsWebhookIntegration:
    """Test Teams bot webhook endpoint."""

    def test_webhook_invalid_bot_id(self, client: TestClient, db_session: Session):
        """Test webhook with invalid bot ID returns error."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        response = client.post(
            "/api/v1/teams-bots/invalid-uuid/webhook",
            json={"type": "message", "text": "test"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_nonexistent_bot(self, client: TestClient, db_session: Session):
        """Test webhook for nonexistent bot returns ok (to prevent retries)."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/teams-bots/{fake_id}/webhook",
            json={"type": "message", "text": "test"},
        )

        # Webhook returns ok or error status but not HTTP error
        assert response.status_code == status.HTTP_200_OK


class TestTeamsBotsAuthorizationIntegration:
    """Test Teams bots authorization."""

    def test_list_bots_unauthorized(self, client: TestClient, db_session: Session):
        """Test that unauthenticated requests to list bots are rejected."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        response = client.get("/api/v1/teams-bots")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_bot_unauthorized(self, client: TestClient, db_session: Session):
        """Test that unauthenticated requests to create bots are rejected."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        bot_data = {
            "agent_id": str(uuid.uuid4()),
            "bot_name": "Unauthorized Bot",
            "app_id": "app-123",
            "app_password": "password",
            "bot_id": "bot-123",
        }

        response = client.post(
            "/api/v1/teams-bots",
            json=bot_data,
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_delete_bot_unauthorized(self, client: TestClient, db_session: Session):
        """Test that unauthenticated requests to delete bots are rejected."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/teams-bots/{fake_id}")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
