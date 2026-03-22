"""
Tests for jira_tools.py - Jira Integration Tools

Tests the Jira tools for issue management, project info, sprints, and boards.
Supports both Basic Auth (API token) and OAuth 2.0 authentication.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestGetJiraBrowseUrl:
    """Tests for _get_jira_browse_url helper function."""

    def test_full_atlassian_domain(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {"domain": "mycompany.atlassian.net"}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://mycompany.atlassian.net/browse/PROJ-123"

    def test_short_domain(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {"domain": "mycompany"}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://mycompany.atlassian.net/browse/PROJ-123"

    def test_domain_with_https_prefix(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {"domain": "https://mycompany.atlassian.net"}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://mycompany.atlassian.net/browse/PROJ-123"

    def test_domain_with_trailing_slash(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {"domain": "mycompany.atlassian.net/"}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://mycompany.atlassian.net/browse/PROJ-123"

    def test_empty_domain_fallback(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {"domain": ""}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://jira.atlassian.com/browse/PROJ-123"

    def test_no_domain_fallback(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_browse_url

        config = {}
        result = _get_jira_browse_url(config, "PROJ-123")
        assert result == "https://jira.atlassian.com/browse/PROJ-123"


class TestGetJiraCredentials:
    """Tests for _get_jira_credentials helper function."""

    @pytest.mark.asyncio
    async def test_raises_error_without_runtime_context(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_credentials

        with pytest.raises(ValueError) as exc_info:
            await _get_jira_credentials(None, "internal_get_jira_issue")

        assert "No runtime context available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_error_when_no_credentials(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_credentials

        mock_resolver = MagicMock()
        mock_resolver.get_jira_credentials = AsyncMock(return_value=None)

        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            with pytest.raises(ValueError) as exc_info:
                await _get_jira_credentials({"agent_id": "test"}, "internal_get_jira_issue")

            assert "Jira authentication not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_returns_credentials_successfully(self):
        from src.services.agents.internal_tools.jira_tools import _get_jira_credentials

        expected_creds = {
            "auth_type": "basic",
            "domain": "mycompany",
            "email": "user@example.com",
            "api_token": "token123",
        }

        mock_resolver = MagicMock()
        mock_resolver.get_jira_credentials = AsyncMock(return_value=expected_creds)

        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            result = await _get_jira_credentials({"agent_id": "test"}, "internal_get_jira_issue")

            assert result == expected_creds


class TestMakeJiraRequest:
    """Tests for _make_jira_request helper function."""

    @pytest.mark.asyncio
    async def test_basic_auth_request(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_request

        config = {
            "auth_type": "basic",
            "domain": "mycompany",
            "email": "user@example.com",
            "api_token": "token123",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            result = await _make_jira_request("GET", "/issue/PROJ-123", config)

            assert result == {"key": "PROJ-123"}

    @pytest.mark.asyncio
    async def test_oauth_request(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_request

        config = {
            "auth_type": "oauth",
            "cloud_id": "cloud-123",
            "access_token": "oauth-token-456",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            result = await _make_jira_request("GET", "/issue/PROJ-123", config)

            assert result == {"key": "PROJ-123"}

            # Verify OAuth URL format
            call_kwargs = mock_instance.request.call_args.kwargs
            assert "api.atlassian.com" in call_kwargs["url"]
            assert "cloud-123" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_oauth_raises_error_without_cloud_id(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_request

        config = {
            "auth_type": "oauth",
            "access_token": "oauth-token-456",
        }

        with pytest.raises(ValueError) as exc_info:
            await _make_jira_request("GET", "/issue/PROJ-123", config)

        assert "cloud_id and access_token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_basic_auth_raises_error_without_domain(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_request

        config = {
            "auth_type": "basic",
            "email": "user@example.com",
            "api_token": "token123",
        }

        with pytest.raises(ValueError) as exc_info:
            await _make_jira_request("GET", "/issue/PROJ-123", config)

        assert "domain, email, and api_token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_post_request_with_json_data(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_request

        config = {
            "auth_type": "basic",
            "domain": "mycompany",
            "email": "user@example.com",
            "api_token": "token123",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            result = await _make_jira_request("POST", "/issue", config, json_data={"fields": {"summary": "Test"}})

            assert result == {"id": "123"}
            call_kwargs = mock_instance.request.call_args.kwargs
            assert call_kwargs["json"] == {"fields": {"summary": "Test"}}


class TestInternalGetJiraIssue:
    """Tests for internal_get_jira_issue function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_credentials(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_issue

        result = await internal_get_jira_issue(issue_key="PROJ-123", runtime_context=None)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_issue_details(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_issue

        mock_issue_data = {
            "key": "PROJ-123",
            "id": "10001",
            "fields": {
                "summary": "Test Issue",
                "description": "Description here",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "reporter": {"displayName": "John Doe"},
                "assignee": {"displayName": "Jane Smith"},
                "created": "2024-01-01T10:00:00Z",
                "updated": "2024-01-02T10:00:00Z",
                "labels": ["urgent"],
                "components": [{"name": "Backend"}],
                "fixVersions": [{"name": "1.0"}],
                "attachment": [],
            },
        }

        mock_comments_data = {
            "comments": [
                {
                    "id": "c1",
                    "body": "A comment",
                    "author": {"displayName": "Commenter"},
                    "created": "2024-01-01T11:00:00Z",
                    "updated": "2024-01-01T11:00:00Z",
                }
            ]
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.side_effect = [mock_issue_data, mock_comments_data]

            result = await internal_get_jira_issue(issue_key="PROJ-123", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["issue"]["key"] == "PROJ-123"
            assert result["issue"]["summary"] == "Test Issue"
            assert result["issue"]["status"] == "Open"
            assert len(result["comments"]) == 1

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_issue

        with patch(
            "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
            new_callable=AsyncMock,
        ) as mock_creds:
            mock_creds.side_effect = Exception("API Error")

            result = await internal_get_jira_issue(issue_key="PROJ-123", runtime_context={"agent_id": "test"})

            assert result["success"] is False
            assert "API Error" in result["error"]


class TestInternalSearchJiraIssues:
    """Tests for internal_search_jira_issues function."""

    @pytest.mark.asyncio
    async def test_searches_with_jql(self):
        from src.services.agents.internal_tools.jira_tools import internal_search_jira_issues

        mock_result = {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "summary": "Issue 1",
                        "status": {"name": "Open"},
                        "priority": {"name": "High"},
                        "assignee": {"displayName": "User"},
                        "created": "2024-01-01",
                        "updated": "2024-01-02",
                    },
                }
            ],
            "total": 1,
            "maxResults": 50,
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_search_jira_issues(jql="project = PROJ", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 1
            assert len(result["issues"]) == 1
            assert result["issues"][0]["key"] == "PROJ-1"

    @pytest.mark.asyncio
    async def test_handles_empty_jql(self):
        from src.services.agents.internal_tools.jira_tools import internal_search_jira_issues

        mock_result = {"issues": [], "total": 0, "maxResults": 50}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_search_jira_issues(jql="", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            # JQL should be normalized to include "project is not EMPTY"
            call_kwargs = mock_request.call_args.kwargs
            assert "project is not EMPTY" in call_kwargs["json_data"]["jql"]

    @pytest.mark.asyncio
    async def test_handles_order_by_only_jql(self):
        from src.services.agents.internal_tools.jira_tools import internal_search_jira_issues

        mock_result = {"issues": [], "total": 0, "maxResults": 50}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_search_jira_issues(
                jql="ORDER BY created DESC", runtime_context={"agent_id": "test"}
            )

            assert result["success"] is True


class TestInternalAddJiraComment:
    """Tests for internal_add_jira_comment function."""

    @pytest.mark.asyncio
    async def test_adds_comment_successfully(self):
        from src.services.agents.internal_tools.jira_tools import internal_add_jira_comment

        mock_result = {
            "id": "comment-123",
            "body": "Test comment",
            "created": "2024-01-01T10:00:00Z",
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_add_jira_comment(
                issue_key="PROJ-123",
                comment_text="Test comment",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["comment_id"] == "comment-123"

    @pytest.mark.asyncio
    async def test_returns_error_on_failure(self):
        from src.services.agents.internal_tools.jira_tools import internal_add_jira_comment

        with patch(
            "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
            new_callable=AsyncMock,
        ) as mock_creds:
            mock_creds.side_effect = Exception("Permission denied")

            result = await internal_add_jira_comment(
                issue_key="PROJ-123",
                comment_text="Test comment",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "Permission denied" in result["error"]


class TestInternalUpdateJiraIssue:
    """Tests for internal_update_jira_issue function."""

    @pytest.mark.asyncio
    async def test_updates_issue_successfully(self):
        from src.services.agents.internal_tools.jira_tools import internal_update_jira_issue

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = {}

            result = await internal_update_jira_issue(
                issue_key="PROJ-123",
                updates={"summary": "New Title", "priority": {"name": "High"}},
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["issue_key"] == "PROJ-123"
            assert "summary" in result["updated_fields"]
            assert "priority" in result["updated_fields"]


class TestInternalTransitionJiraIssue:
    """Tests for internal_transition_jira_issue function."""

    @pytest.mark.asyncio
    async def test_transitions_issue_successfully(self):
        from src.services.agents.internal_tools.jira_tools import internal_transition_jira_issue

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = {}

            result = await internal_transition_jira_issue(
                issue_key="PROJ-123",
                transition_id="21",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["issue_key"] == "PROJ-123"
            assert result["transition_id"] == "21"


class TestInternalGetJiraProject:
    """Tests for internal_get_jira_project function."""

    @pytest.mark.asyncio
    async def test_returns_project_info(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_project

        mock_result = {
            "key": "PROJ",
            "name": "My Project",
            "description": "Project description",
            "lead": {"displayName": "Project Lead"},
            "self": "https://api.atlassian.com/...",
            "issueTypes": [{"name": "Bug"}, {"name": "Task"}],
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_project(project_key="PROJ", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["project"]["key"] == "PROJ"
            assert result["project"]["name"] == "My Project"
            assert "Bug" in result["project"]["issue_types"]


class TestInternalCreateJiraIssue:
    """Tests for internal_create_jira_issue function."""

    @pytest.mark.asyncio
    async def test_creates_issue_with_minimal_fields(self):
        from src.services.agents.internal_tools.jira_tools import internal_create_jira_issue

        mock_result = {"id": "10001", "key": "PROJ-124"}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_create_jira_issue(
                project_key="PROJ",
                summary="New Issue",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["issue"]["key"] == "PROJ-124"

    @pytest.mark.asyncio
    async def test_creates_issue_with_all_fields(self):
        from src.services.agents.internal_tools.jira_tools import internal_create_jira_issue

        mock_result = {"id": "10002", "key": "PROJ-125"}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_create_jira_issue(
                project_key="PROJ",
                summary="Bug Report",
                issue_type="Bug",
                description="Detailed description",
                priority="High",
                assignee_account_id="user-123",
                labels=["urgent", "frontend"],
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["issue"]["key"] == "PROJ-125"

            # Verify the request included all fields
            call_kwargs = mock_request.call_args.kwargs
            fields = call_kwargs["json_data"]["fields"]
            assert fields["issuetype"]["name"] == "Bug"
            assert fields["priority"]["name"] == "High"
            assert fields["assignee"]["accountId"] == "user-123"
            assert fields["labels"] == ["urgent", "frontend"]


class TestInternalGetJiraBoards:
    """Tests for internal_get_jira_boards function."""

    @pytest.mark.asyncio
    async def test_returns_boards_list(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_boards

        mock_result = {
            "values": [
                {
                    "id": 1,
                    "name": "Team Board",
                    "type": "scrum",
                    "location": {"projectKey": "PROJ"},
                },
                {
                    "id": 2,
                    "name": "Kanban Board",
                    "type": "kanban",
                    "location": {"projectKey": "PROJ"},
                },
            ],
            "total": 2,
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_boards(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["boards"]) == 2

    @pytest.mark.asyncio
    async def test_filters_by_project_key(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_boards

        mock_result = {"values": [], "total": 0}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_boards(project_key="PROJ", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["params"]["projectKeyOrId"] == "PROJ"


class TestInternalGetJiraSprints:
    """Tests for internal_get_jira_sprints function."""

    @pytest.mark.asyncio
    async def test_returns_sprints_list(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_sprints

        mock_result = {
            "values": [
                {
                    "id": 1,
                    "name": "Sprint 1",
                    "state": "closed",
                    "startDate": "2024-01-01",
                    "endDate": "2024-01-14",
                    "completeDate": "2024-01-14",
                    "goal": "Complete feature X",
                },
                {
                    "id": 2,
                    "name": "Sprint 2",
                    "state": "active",
                    "startDate": "2024-01-15",
                    "endDate": "2024-01-28",
                },
            ],
            "total": 2,
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_sprints(board_id=1, runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 2
            assert result["sprints"][0]["name"] == "Sprint 1"

    @pytest.mark.asyncio
    async def test_filters_by_state(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_sprints

        mock_result = {"values": [], "total": 0}

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_sprints(board_id=1, state="active", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["params"]["state"] == "active"


class TestInternalGetSprintIssues:
    """Tests for internal_get_sprint_issues function."""

    @pytest.mark.asyncio
    async def test_returns_sprint_issues_with_summary(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_sprint_issues

        mock_result = {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "summary": "Task 1",
                        "status": {"name": "Done"},
                        "priority": {"name": "High"},
                        "assignee": {"displayName": "User A"},
                        "customfield_10016": 3,
                    },
                },
                {
                    "key": "PROJ-2",
                    "fields": {
                        "summary": "Task 2",
                        "status": {"name": "In Progress"},
                        "priority": {"name": "Medium"},
                        "assignee": {"displayName": "User A"},
                        "customfield_10016": 5,
                    },
                },
                {
                    "key": "PROJ-3",
                    "fields": {
                        "summary": "Task 3",
                        "status": {"name": "Done"},
                        "priority": None,
                        "assignee": None,
                    },
                },
            ]
        }

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_sprint_issues(sprint_id=1, runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 3

            # Check summary
            assert result["summary"]["by_status"]["Done"] == 2
            assert result["summary"]["by_status"]["In Progress"] == 1
            assert result["summary"]["by_assignee"]["User A"] == 2
            assert result["summary"]["by_assignee"]["Unassigned"] == 1


class TestInternalStartJiraSprint:
    """Tests for internal_start_jira_sprint function."""

    @pytest.mark.asyncio
    async def test_starts_sprint_successfully(self):
        from src.services.agents.internal_tools.jira_tools import internal_start_jira_sprint

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = {}

            result = await internal_start_jira_sprint(
                sprint_id=1,
                end_date="2024-01-28T00:00:00Z",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["sprint_id"] == 1
            assert result["state"] == "active"

    @pytest.mark.asyncio
    async def test_uses_custom_start_date(self):
        from src.services.agents.internal_tools.jira_tools import internal_start_jira_sprint

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = {}

            result = await internal_start_jira_sprint(
                sprint_id=1,
                start_date="2024-01-15T00:00:00Z",
                end_date="2024-01-28T00:00:00Z",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["json_data"]["startDate"] == "2024-01-15T00:00:00Z"


class TestInternalCloseJiraSprint:
    """Tests for internal_close_jira_sprint function."""

    @pytest.mark.asyncio
    async def test_closes_sprint_successfully(self):
        from src.services.agents.internal_tools.jira_tools import internal_close_jira_sprint

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_agile_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = {}

            result = await internal_close_jira_sprint(sprint_id=1, runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["sprint_id"] == 1
            assert result["state"] == "closed"


class TestInternalGetJiraUsers:
    """Tests for internal_get_jira_users function."""

    @pytest.mark.asyncio
    async def test_returns_users_list(self):
        from src.services.agents.internal_tools.jira_tools import internal_get_jira_users

        mock_result = [
            {
                "accountId": "user-123",
                "displayName": "John Doe",
                "emailAddress": "john@example.com",
                "active": True,
            },
            {
                "accountId": "user-456",
                "displayName": "Jane Smith",
                "emailAddress": "jane@example.com",
                "active": True,
            },
        ]

        with (
            patch(
                "src.services.agents.internal_tools.jira_tools._get_jira_credentials",
                new_callable=AsyncMock,
            ) as mock_creds,
            patch(
                "src.services.agents.internal_tools.jira_tools._make_jira_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_creds.return_value = {"domain": "mycompany", "auth_type": "basic"}
            mock_request.return_value = mock_result

            result = await internal_get_jira_users(project_key="PROJ", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 2
            assert result["users"][0]["account_id"] == "user-123"
            assert result["users"][0]["display_name"] == "John Doe"


class TestMakeJiraAgileRequest:
    """Tests for _make_jira_agile_request helper function."""

    @pytest.mark.asyncio
    async def test_basic_auth_uses_agile_api(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_agile_request

        config = {
            "auth_type": "basic",
            "domain": "mycompany",
            "email": "user@example.com",
            "api_token": "token123",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"values": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            result = await _make_jira_agile_request("GET", "/board", config)

            assert result == {"values": []}

            # Verify agile API URL format
            call_kwargs = mock_instance.request.call_args.kwargs
            assert "/rest/agile/1.0/board" in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_oauth_uses_agile_api(self):
        from src.services.agents.internal_tools.jira_tools import _make_jira_agile_request

        config = {
            "auth_type": "oauth",
            "cloud_id": "cloud-123",
            "access_token": "oauth-token",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"values": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.request = AsyncMock(return_value=mock_response)

            await _make_jira_agile_request("GET", "/board", config)

            call_kwargs = mock_instance.request.call_args.kwargs
            assert "api.atlassian.com" in call_kwargs["url"]
            assert "/rest/agile/1.0/board" in call_kwargs["url"]
