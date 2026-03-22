"""
Tests for clickup_tools.py - ClickUp Integration

Tests the ClickUp task management integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalGetClickupTask:
    """Tests for internal_get_clickup_task function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_task

        result = await internal_get_clickup_task(task_id="abc123", runtime_context=None)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_gets_task_successfully(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_task

        mock_task_data = {
            "id": "abc123",
            "name": "Fix bug",
            "description": "Fix the login bug",
            "status": {"status": "in progress"},
            "priority": {"priority": "high"},
            "due_date": "1704067200000",
            "creator": {"username": "dev1"},
            "assignees": [{"username": "dev2"}],
            "tags": [{"name": "bug"}],
            "custom_fields": [],
            "url": "https://app.clickup.com/t/abc123",
            "date_created": "1704000000000",
            "date_updated": "1704067200000",
            "attachments": [],
        }
        mock_comments_data = {
            "comments": [
                {"id": "c1", "comment_text": "Looking into this", "user": {"username": "dev1"}, "date": "1704067200000"}
            ]
        }

        with (
            patch(
                "src.services.agents.internal_tools.clickup_tools._get_clickup_token",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.clickup_tools._make_clickup_request",
                new_callable=AsyncMock,
                side_effect=[mock_task_data, mock_comments_data],
            ),
        ):
            result = await internal_get_clickup_task(task_id="abc123", runtime_context=MagicMock())
            assert result["success"] is True
            assert result["task"]["id"] == "abc123"
            assert result["task"]["name"] == "Fix bug"


class TestInternalSearchClickupTasks:
    """Tests for internal_search_clickup_tasks function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_search_clickup_tasks

        result = await internal_search_clickup_tasks(list_id="list1", runtime_context=None)
        assert result["success"] is False


class TestInternalAddClickupComment:
    """Tests for internal_add_clickup_comment function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_add_clickup_comment

        result = await internal_add_clickup_comment(task_id="abc", comment_text="test", runtime_context=None)
        assert result["success"] is False


class TestInternalUpdateClickupTask:
    """Tests for internal_update_clickup_task function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_update_clickup_task

        result = await internal_update_clickup_task(task_id="abc", updates={"name": "new"}, runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupWorkspace:
    """Tests for internal_get_clickup_workspace function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_workspace

        result = await internal_get_clickup_workspace(runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupSpaces:
    """Tests for internal_get_clickup_spaces function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_spaces

        result = await internal_get_clickup_spaces(team_id="team1", runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupFolders:
    """Tests for internal_get_clickup_folders function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_folders

        result = await internal_get_clickup_folders(space_id="space1", runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupLists:
    """Tests for internal_get_clickup_lists function."""

    @pytest.mark.asyncio
    async def test_requires_folder_id_or_space_id(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_lists

        result = await internal_get_clickup_lists(runtime_context=MagicMock())
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_lists

        result = await internal_get_clickup_lists(folder_id="f1", runtime_context=None)
        assert result["success"] is False


class TestInternalCreateClickupTask:
    """Tests for internal_create_clickup_task function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_create_clickup_task

        result = await internal_create_clickup_task(list_id="l1", name="New Task", runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupMembers:
    """Tests for internal_get_clickup_members function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_members

        result = await internal_get_clickup_members(team_id="team1", runtime_context=None)
        assert result["success"] is False


class TestInternalGetClickupListSummary:
    """Tests for internal_get_clickup_list_summary function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_runtime_context(self):
        from src.services.agents.internal_tools.clickup_tools import internal_get_clickup_list_summary

        result = await internal_get_clickup_list_summary(list_id="l1", runtime_context=None)
        assert result["success"] is False
