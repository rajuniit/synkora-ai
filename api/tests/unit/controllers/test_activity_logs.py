"""Tests for activity logs controller."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.activity_logs import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.tenant import AccountRole


@pytest.fixture
def mock_activity_service():
    with patch("src.controllers.activity_logs.ActivityLogService") as mock:
        # Make the instance an AsyncMock so all methods are awaitable
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def mock_team_service():
    with patch("src.services.team.team_service.TeamService") as mock:
        # Make the instance an AsyncMock so all methods are awaitable
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def client(mock_activity_service, mock_team_service):
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies - use async generator for async db
    async def mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_async_db] = mock_db

    # Mock current account
    mock_account = MagicMock()
    mock_account.id = uuid.uuid4()
    app.dependency_overrides[get_current_account] = lambda: mock_account

    # Mock tenant ID
    tenant_id = uuid.uuid4()
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    return TestClient(app), tenant_id, mock_account, {"activity": mock_activity_service, "team": mock_team_service}


class TestListActivityLogs:
    """Tests for listing activity logs."""

    def test_list_activity_logs_as_owner(self, client):
        """Test owner can list all activity logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        # Mock team member as owner
        mock_team.get_team_member.return_value = {"role": AccountRole.OWNER.value}

        # Mock logs
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = str(tenant_id)
        mock_log.account_id = str(uuid.uuid4())
        mock_log.account_name = "Test User"
        mock_log.account_email = "test@example.com"
        mock_log.action = "create"
        mock_log.resource_type = "agent"
        mock_log.resource_id = str(uuid.uuid4())
        mock_log.details = {"key": "value"}
        mock_log.ip_address = "127.0.0.1"
        mock_log.user_agent = "TestClient"
        mock_log.created_at = datetime.now(UTC).isoformat()

        mock_activity.list_logs.return_value = [mock_log]

        response = test_client.get("/api/v1/activity-logs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["action"] == "create"

    def test_list_activity_logs_as_admin(self, client):
        """Test admin can list all activity logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        # Mock team member as admin
        mock_team.get_team_member.return_value = {"role": AccountRole.ADMIN.value}

        mock_activity.list_logs.return_value = []

        response = test_client.get("/api/v1/activity-logs")

        assert response.status_code == status.HTTP_200_OK

    def test_list_activity_logs_as_member_only_own(self, client):
        """Test regular member can only see their own logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        # Mock team member as regular member
        mock_team.get_team_member.return_value = {"role": "member"}

        mock_activity.list_logs.return_value = []

        response = test_client.get("/api/v1/activity-logs")

        assert response.status_code == status.HTTP_200_OK
        # Verify that list_logs was called with the current account's ID
        mock_activity.list_logs.assert_called_once()
        call_kwargs = mock_activity.list_logs.call_args[1]
        assert call_kwargs["account_id"] == str(mock_account.id)

    def test_list_activity_logs_not_team_member(self, client):
        """Test non-team member gets access denied."""
        test_client, tenant_id, mock_account, mocks = client
        mock_team = mocks["team"].return_value

        # Mock no team membership
        mock_team.get_team_member.return_value = None

        response = test_client.get("/api/v1/activity-logs")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_activity_logs_with_filters(self, client):
        """Test listing logs with filters."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.OWNER.value}
        mock_activity.list_logs.return_value = []

        response = test_client.get("/api/v1/activity-logs?action=create&resource_type=agent&skip=10&limit=50")

        assert response.status_code == status.HTTP_200_OK
        mock_activity.list_logs.assert_called_once()
        call_kwargs = mock_activity.list_logs.call_args[1]
        assert call_kwargs["action"] == "create"
        assert call_kwargs["resource_type"] == "agent"
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 50


class TestGetActivityStats:
    """Tests for getting activity statistics."""

    def test_get_activity_stats_as_owner(self, client):
        """Test owner can get activity stats."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.OWNER.value}

        mock_stats = {
            "total_activities": 100,
            "unique_users": 5,
            "top_actions": [{"action": "create", "count": 50}],
            "recent_activities": [],
        }
        mock_activity.get_stats.return_value = mock_stats

        response = test_client.get("/api/v1/activity-logs/stats?days=30")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_activities"] == 100

    def test_get_activity_stats_as_admin(self, client):
        """Test admin can get activity stats."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.ADMIN.value}

        mock_stats = {"total_activities": 50, "unique_users": 3, "top_actions": [], "recent_activities": []}
        mock_activity.get_stats.return_value = mock_stats

        response = test_client.get("/api/v1/activity-logs/stats")

        assert response.status_code == status.HTTP_200_OK

    def test_get_activity_stats_forbidden_for_member(self, client):
        """Test regular member cannot get activity stats."""
        test_client, tenant_id, mock_account, mocks = client
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": "member"}

        response = test_client.get("/api/v1/activity-logs/stats")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetActivityLog:
    """Tests for getting a specific activity log."""

    def test_get_activity_log_as_owner(self, client):
        """Test owner can get any activity log."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.OWNER.value}

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = str(tenant_id)
        mock_log.account_id = str(uuid.uuid4())  # Different user
        mock_log.account_name = "Other User"
        mock_log.account_email = "other@example.com"
        mock_log.action = "update"
        mock_log.resource_type = "agent"
        mock_log.resource_id = str(uuid.uuid4())
        mock_log.details = {}
        mock_log.ip_address = "127.0.0.1"
        mock_log.user_agent = "TestClient"
        mock_log.created_at = datetime.now(UTC).isoformat()

        mock_activity.get_log.return_value = mock_log

        response = test_client.get("/api/v1/activity-logs/1")

        assert response.status_code == status.HTTP_200_OK

    def test_get_activity_log_not_found(self, client):
        """Test getting non-existent log returns 404."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value

        mock_activity.get_log.return_value = None

        response = test_client.get("/api/v1/activity-logs/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_activity_log_wrong_tenant(self, client):
        """Test getting log from different tenant is forbidden."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = uuid.uuid4()  # Different tenant

        mock_activity.get_log.return_value = mock_log

        response = test_client.get("/api/v1/activity-logs/1")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_activity_log_member_own_log(self, client):
        """Test regular member can get their own log."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": "member"}

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = str(tenant_id)
        mock_log.account_id = str(mock_account.id)  # Own log
        mock_log.account_name = "Test User"
        mock_log.account_email = "test@example.com"
        mock_log.action = "create"
        mock_log.resource_type = "agent"
        mock_log.resource_id = str(uuid.uuid4())
        mock_log.details = {}
        mock_log.ip_address = "127.0.0.1"
        mock_log.user_agent = "TestClient"
        mock_log.created_at = datetime.now(UTC).isoformat()

        mock_activity.get_log.return_value = mock_log

        response = test_client.get("/api/v1/activity-logs/1")

        assert response.status_code == status.HTTP_200_OK

    def test_get_activity_log_member_other_log(self, client):
        """Test regular member cannot get other's log."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": "member"}

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = tenant_id
        mock_log.account_id = uuid.uuid4()  # Different user

        mock_activity.get_log.return_value = mock_log

        response = test_client.get("/api/v1/activity-logs/1")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetMyRecentActivities:
    """Tests for getting current user's recent activities."""

    def test_get_my_recent_activities(self, client):
        """Test getting own recent activities."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value

        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.tenant_id = str(tenant_id)
        mock_log.account_id = str(mock_account.id)
        mock_log.account_name = "Test User"
        mock_log.account_email = "test@example.com"
        mock_log.action = "create"
        mock_log.resource_type = "agent"
        mock_log.resource_id = str(uuid.uuid4())
        mock_log.details = {}
        mock_log.ip_address = "127.0.0.1"
        mock_log.user_agent = "TestClient"
        mock_log.created_at = datetime.now(UTC).isoformat()

        mock_activity.list_logs.return_value = [mock_log]

        response = test_client.get("/api/v1/activity-logs/me/recent?limit=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1


class TestCleanupOldLogs:
    """Tests for cleaning up old activity logs."""

    def test_cleanup_logs_as_owner(self, client):
        """Test owner can cleanup old logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_activity = mocks["activity"].return_value
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.OWNER.value}

        response = test_client.delete("/api/v1/activity-logs/cleanup?days=90")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_activity.cleanup_old_logs.assert_called_once()

    def test_cleanup_logs_forbidden_for_admin(self, client):
        """Test admin cannot cleanup logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": AccountRole.ADMIN.value}

        response = test_client.delete("/api/v1/activity-logs/cleanup?days=90")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cleanup_logs_forbidden_for_member(self, client):
        """Test regular member cannot cleanup logs."""
        test_client, tenant_id, mock_account, mocks = client
        mock_team = mocks["team"].return_value

        mock_team.get_team_member.return_value = {"role": "member"}

        response = test_client.delete("/api/v1/activity-logs/cleanup?days=90")

        assert response.status_code == status.HTTP_403_FORBIDDEN
