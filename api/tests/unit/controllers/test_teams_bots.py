"""Tests for Teams bots controller."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.teams_bots import teams_router as router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def client(mock_db_session):
    app = FastAPI()
    app.include_router(router)

    tenant_id = uuid.uuid4()

    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    yield TestClient(app), tenant_id, mock_db_session


def _create_mock_agent(tenant_id):
    """Helper to create a mock agent."""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.tenant_id = tenant_id
    agent.agent_name = "Test Agent"
    return agent


def _create_mock_teams_bot(tenant_id, agent):
    """Helper to create a mock Teams bot."""
    bot = MagicMock()
    bot.id = uuid.uuid4()
    bot.agent_id = agent.id
    bot.agent = agent
    bot.tenant_id = tenant_id
    bot.bot_name = "Test Teams Bot"
    bot.app_id = "app-123"
    bot.bot_id = "bot-456"
    bot.webhook_url = "https://example.com/webhook"
    bot.welcome_message = "Hello!"
    bot.is_active = True
    bot.last_message_at = None
    bot.created_at = datetime.now(UTC)
    bot.updated_at = datetime.now(UTC)
    return bot


def _create_mock_result(value):
    """Helper to create a mock async db result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    mock_result.scalars.return_value.all.return_value = [value] if value else []
    return mock_result


class TestCreateTeamsBot:
    """Tests for creating Teams bots."""

    def test_create_teams_bot_success(self, client):
        """Test successfully creating a Teams bot."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        # Mock db.execute to return agent
        mock_db.execute.return_value = _create_mock_result(agent)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with (
            patch("src.controllers.teams_bots.TeamsBot") as MockTeamsBot,
            patch("src.controllers.teams_bots.encrypt_value") as mock_encrypt,
        ):
            MockTeamsBot.return_value = mock_bot
            mock_encrypt.return_value = "encrypted_password"

            response = test_client.post(
                "/teams-bots",
                json={
                    "agent_id": str(agent.id),
                    "bot_name": "Test Teams Bot",
                    "app_id": "app-123",
                    "app_password": "secret-password",
                    "bot_id": "bot-456",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["bot_name"] == "Test Teams Bot"

    def test_create_teams_bot_agent_not_found(self, client):
        """Test creating bot with non-existent agent."""
        test_client, tenant_id, mock_db = client

        # Mock db.execute to return None (agent not found)
        mock_db.execute.return_value = _create_mock_result(None)

        response = test_client.post(
            "/teams-bots",
            json={
                "agent_id": str(uuid.uuid4()),
                "bot_name": "Test Bot",
                "app_id": "app-123",
                "app_password": "secret",
                "bot_id": "bot-456",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_teams_bot_invalid_agent_id(self, client):
        """Test creating bot with invalid agent ID format."""
        test_client, tenant_id, mock_db = client

        response = test_client.post(
            "/teams-bots",
            json={
                "agent_id": "invalid-uuid",
                "bot_name": "Test Bot",
                "app_id": "app-123",
                "app_password": "secret",
                "bot_id": "bot-456",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestListTeamsBots:
    """Tests for listing Teams bots."""

    def test_list_teams_bots_success(self, client):
        """Test successfully listing Teams bots."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        # Mock db.execute result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_bot]
        mock_db.execute.return_value = mock_result

        response = test_client.get("/teams-bots")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["bots"]) == 1

    def test_list_teams_bots_with_agent_filter(self, client):
        """Test listing bots filtered by agent."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_bot]
        mock_db.execute.return_value = mock_result

        response = test_client.get(f"/teams-bots?agent_id={agent.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_list_teams_bots_empty(self, client):
        """Test listing bots when none exist."""
        test_client, tenant_id, mock_db = client

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = test_client.get("/teams-bots")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["bots"]) == 0


class TestGetTeamsBot:
    """Tests for getting a Teams bot."""

    def test_get_teams_bot_success(self, client):
        """Test successfully getting a Teams bot."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        mock_db.execute.return_value = _create_mock_result(mock_bot)

        response = test_client.get(f"/teams-bots/{mock_bot.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_get_teams_bot_not_found(self, client):
        """Test getting non-existent bot."""
        test_client, tenant_id, mock_db = client

        mock_db.execute.return_value = _create_mock_result(None)

        response = test_client.get(f"/teams-bots/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_teams_bot_invalid_id(self, client):
        """Test getting bot with invalid ID format."""
        test_client, tenant_id, mock_db = client

        response = test_client.get("/teams-bots/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdateTeamsBot:
    """Tests for updating Teams bots."""

    def test_update_teams_bot_success(self, client):
        """Test successfully updating a Teams bot."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        mock_db.execute.return_value = _create_mock_result(mock_bot)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("src.controllers.teams_bots.encrypt_value") as mock_encrypt:
            mock_encrypt.return_value = "encrypted"

            response = test_client.put(f"/teams-bots/{mock_bot.id}", json={"bot_name": "Updated Bot Name"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_update_teams_bot_not_found(self, client):
        """Test updating non-existent bot."""
        test_client, tenant_id, mock_db = client

        mock_db.execute.return_value = _create_mock_result(None)

        response = test_client.put(f"/teams-bots/{uuid.uuid4()}", json={"bot_name": "Updated"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_teams_bot_with_password(self, client):
        """Test updating bot with new password."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        mock_db.execute.return_value = _create_mock_result(mock_bot)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("src.controllers.teams_bots.encrypt_value") as mock_encrypt:
            mock_encrypt.return_value = "new_encrypted"

            response = test_client.put(f"/teams-bots/{mock_bot.id}", json={"app_password": "new-password"})

        assert response.status_code == status.HTTP_200_OK
        mock_encrypt.assert_called_once_with("new-password")


class TestDeleteTeamsBot:
    """Tests for deleting Teams bots."""

    def test_delete_teams_bot_success(self, client):
        """Test successfully deleting a Teams bot."""
        test_client, tenant_id, mock_db = client

        agent = _create_mock_agent(tenant_id)
        mock_bot = _create_mock_teams_bot(tenant_id, agent)

        mock_db.execute.return_value = _create_mock_result(mock_bot)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        response = test_client.delete(f"/teams-bots/{mock_bot.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

    def test_delete_teams_bot_not_found(self, client):
        """Test deleting non-existent bot."""
        test_client, tenant_id, mock_db = client

        mock_db.execute.return_value = _create_mock_result(None)

        response = test_client.delete(f"/teams-bots/{uuid.uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeamsWebhook:
    """Tests for Teams webhook endpoint."""

    def test_handle_webhook_success(self, client):
        """Test handling incoming webhook."""
        test_client, tenant_id, mock_db = client

        bot_id = uuid.uuid4()

        with patch("src.controllers.teams_bots.TeamsWebhookService") as MockService:
            mock_service = MockService.return_value
            mock_service.handle_activity = AsyncMock()

            response = test_client.post(f"/teams-bots/{bot_id}/webhook", json={"type": "message", "text": "Hello!"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"

    def test_handle_webhook_invalid_bot_id(self, client):
        """Test webhook with invalid bot ID."""
        test_client, tenant_id, mock_db = client

        response = test_client.post("/teams-bots/invalid-uuid/webhook", json={"type": "message"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_handle_webhook_error(self, client):
        """Test webhook handling error."""
        test_client, tenant_id, mock_db = client

        bot_id = uuid.uuid4()

        with patch("src.controllers.teams_bots.TeamsWebhookService") as MockService:
            mock_service = MockService.return_value
            mock_service.handle_activity = AsyncMock(side_effect=Exception("Error"))

            response = test_client.post(f"/teams-bots/{bot_id}/webhook", json={"type": "message"})

        # Should still return 200 to prevent retries
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
