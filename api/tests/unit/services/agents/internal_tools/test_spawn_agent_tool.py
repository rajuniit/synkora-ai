"""
Tests for spawn_agent_tool.py - Sub-Agent Spawning

Tests the tools for spawning sub-agents for complex, multi-step,
or long-running tasks using Celery background execution.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalSpawnAgent:
    """Tests for internal_spawn_agent function."""

    @pytest.mark.asyncio
    async def test_requires_task_description(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        result = await internal_spawn_agent(
            task_description="",
            tenant_id="tenant-123",
            parent_agent_id="agent-123",
        )

        assert result["success"] is False
        assert "task_description is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_task_description_not_whitespace(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        result = await internal_spawn_agent(
            task_description="   ",
            tenant_id="tenant-123",
            parent_agent_id="agent-123",
        )

        assert result["success"] is False
        assert "task_description is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_tenant_id(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        result = await internal_spawn_agent(
            task_description="Research AI frameworks",
            tenant_id=None,
            parent_agent_id="agent-123",
        )

        assert result["success"] is False
        assert "tenant_id" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_parent_agent_id(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        result = await internal_spawn_agent(
            task_description="Research AI frameworks",
            tenant_id="tenant-123",
            parent_agent_id=None,
        )

        assert result["success"] is False
        assert "parent_agent_id" in result["error"]

    @pytest.mark.asyncio
    async def test_background_task_returns_task_id(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        mock_celery_result = MagicMock()
        mock_celery_result.id = "task-12345"

        with patch("src.tasks.agent_tasks.execute_spawn_agent_task") as mock_task:
            mock_task.delay.return_value = mock_celery_result

            result = await internal_spawn_agent(
                task_description="Analyze error logs",
                run_in_background=True,
                tenant_id="tenant-123",
                parent_agent_id="agent-123",
            )

            assert result["success"] is True
            assert result["task_id"] == "task-12345"
            assert "check_task" in result["message"]

    @pytest.mark.asyncio
    async def test_synchronous_execution_returns_result(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_spawn_agent

        # Mock the _execute_sub_agent function
        with patch(
            "src.services.agents.internal_tools.spawn_agent_tool._execute_sub_agent", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = "Task completed successfully"

            result = await internal_spawn_agent(
                task_description="Quick analysis",
                run_in_background=False,
                tenant_id="tenant-123",
                parent_agent_id="agent-123",
                parent_agent_name="TestAgent",
            )

            assert result["success"] is True
            assert result["result"] == "Task completed successfully"


class TestInternalCheckTask:
    """Tests for internal_check_task function."""

    @pytest.mark.asyncio
    async def test_requires_task_id(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        result = await internal_check_task(task_id="")

        assert result["success"] is False
        assert "task_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_pending_status(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "PENDING"
        mock_async_result.successful.return_value = False
        mock_async_result.failed.return_value = False

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_returns_running_status(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "STARTED"
        mock_async_result.successful.return_value = False
        mock_async_result.failed.return_value = False

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_returns_completed_with_result(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "SUCCESS"
        mock_async_result.successful.return_value = True
        mock_async_result.failed.return_value = False
        mock_async_result.result = {"success": True, "result": "Analysis complete"}

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "completed"
            assert result["result"] == "Analysis complete"

    @pytest.mark.asyncio
    async def test_returns_failed_status(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "FAILURE"
        mock_async_result.successful.return_value = False
        mock_async_result.failed.return_value = True
        mock_async_result.result = Exception("Task execution failed")

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_retrying_status(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "RETRY"
        mock_async_result.successful.return_value = False
        mock_async_result.failed.return_value = False

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "retrying"

    @pytest.mark.asyncio
    async def test_returns_cancelled_status(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_check_task

        mock_async_result = MagicMock()
        mock_async_result.state = "REVOKED"
        mock_async_result.successful.return_value = False
        mock_async_result.failed.return_value = False

        with patch("celery.result.AsyncResult", return_value=mock_async_result):
            result = await internal_check_task(task_id="task-12345")

            assert result["success"] is True
            assert result["status"] == "cancelled"


class TestInternalListBackgroundTasks:
    """Tests for internal_list_background_tasks function."""

    @pytest.mark.asyncio
    async def test_returns_guidance_message(self):
        from src.services.agents.internal_tools.spawn_agent_tool import internal_list_background_tasks

        result = await internal_list_background_tasks()

        assert result["success"] is True
        assert "check_task" in result["message"]
        assert "note" in result
