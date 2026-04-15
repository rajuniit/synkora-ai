"""
Tests for scheduler_tools.py - Scheduled Task Management Tools

Tests the scheduler tools for creating, listing, deleting, and toggling
scheduled tasks with both interval-based and cron-based scheduling.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestInternalCreateScheduledTask:
    """Tests for internal_create_scheduled_task function."""

    @pytest.mark.asyncio
    async def test_requires_account_id(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        result = await internal_create_scheduled_task(
            db=mock_db,
            tenant_id=str(uuid4()),
            name="Test Task",
            task_type="agent_task",
            interval_seconds=3600,
            config={"task": "config"},
        )

        assert result["success"] is False
        assert "Account ID" in result["error"]

    @pytest.mark.asyncio
    async def test_creates_interval_task_successfully(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.name = "Daily Report"
        mock_task.interval_seconds = 86400
        mock_task.is_active = True

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.create_agent_task = AsyncMock(return_value=mock_task)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_create_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Daily Report",
                task_type="report",
                interval_seconds=86400,
                config={"report_type": "daily"},
                account_id=str(uuid4()),
            )

            assert result["success"] is True
            assert result["task_id"] == str(task_id)
            assert "every 1 day" in result["message"]

    @pytest.mark.asyncio
    async def test_formats_hour_interval_display(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.name = "Hourly Check"
        mock_task.interval_seconds = 7200  # 2 hours
        mock_task.is_active = True

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.create_agent_task = AsyncMock(return_value=mock_task)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_create_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Hourly Check",
                task_type="check",
                interval_seconds=7200,
                config={},
                account_id=str(uuid4()),
            )

            assert result["success"] is True
            assert "every 2 hour" in result["message"]

    @pytest.mark.asyncio
    async def test_formats_minute_interval_display(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.name = "Quick Check"
        mock_task.interval_seconds = 300  # 5 minutes
        mock_task.is_active = True

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.create_agent_task = AsyncMock(return_value=mock_task)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_create_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Quick Check",
                task_type="check",
                interval_seconds=300,
                config={},
                account_id=str(uuid4()),
            )

            assert result["success"] is True
            assert "every 5 minute" in result["message"]

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.agents.internal_tools.scheduler_tools.SchedulerService") as mock_service:
            mock_service.side_effect = Exception("Database error")

            result = await internal_create_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Test Task",
                task_type="test",
                interval_seconds=3600,
                config={},
                account_id=str(uuid4()),
            )

            assert result["success"] is False
            assert "Database error" in result["error"]


class TestInternalCreateCronScheduledTask:
    """Tests for internal_create_cron_scheduled_task function."""

    @pytest.mark.asyncio
    async def test_requires_account_id(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_cron_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        result = await internal_create_cron_scheduled_task(
            db=mock_db,
            tenant_id=str(uuid4()),
            name="Test Task",
            task_type="agent_task",
            cron_expression="0 7 * * *",
            config={},
        )

        assert result["success"] is False
        assert "Account ID" in result["error"]

    @pytest.mark.asyncio
    async def test_creates_cron_task_successfully(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_cron_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.name = "Morning Report"
        mock_task.cron_expression = "0 7 * * *"
        mock_task.is_active = True

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.create_task = AsyncMock(return_value=mock_task)
        mock_scheduler_service.validate_cron.return_value = {
            "valid": True,
            "description": "Every day at 7:00 AM",
            "next_runs": ["2025-01-10T07:00:00", "2025-01-11T07:00:00", "2025-01-12T07:00:00"],
        }

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_create_cron_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Morning Report",
                task_type="report",
                cron_expression="0 7 * * *",
                config={"report_type": "daily"},
                account_id=str(uuid4()),
            )

            assert result["success"] is True
            assert result["task_id"] == str(task_id)
            assert "7:00 AM" in result["schedule_description"]

    @pytest.mark.asyncio
    async def test_handles_invalid_cron_expression(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_create_cron_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.create_task = AsyncMock(side_effect=ValueError("Invalid cron expression"))

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_create_cron_scheduled_task(
                db=mock_db,
                tenant_id=str(uuid4()),
                name="Bad Task",
                task_type="test",
                cron_expression="invalid cron",
                config={},
                account_id=str(uuid4()),
            )

            assert result["success"] is False
            assert "Invalid cron expression" in result["error"]


class TestInternalListScheduledTasks:
    """Tests for internal_list_scheduled_tasks function."""

    @pytest.mark.asyncio
    async def test_lists_tasks_successfully(self):
        from datetime import datetime

        from src.services.agents.internal_tools.scheduler_tools import internal_list_scheduled_tasks

        mock_db = AsyncMock(spec=AsyncSession)

        mock_task1 = MagicMock()
        mock_task1.id = uuid4()
        mock_task1.name = "Task 1"
        mock_task1.task_type = "report"
        mock_task1.interval_seconds = 3600
        mock_task1.is_active = True
        mock_task1.last_run_at = datetime(2025, 1, 10, 10, 0, 0)
        mock_task1.created_at = datetime(2025, 1, 1, 0, 0, 0)

        mock_task2 = MagicMock()
        mock_task2.id = uuid4()
        mock_task2.name = "Task 2"
        mock_task2.task_type = "check"
        mock_task2.interval_seconds = 300
        mock_task2.is_active = False
        mock_task2.last_run_at = None
        mock_task2.created_at = datetime(2025, 1, 5, 0, 0, 0)

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.list_tasks = AsyncMock(return_value=[mock_task1, mock_task2])

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_list_scheduled_tasks(
                db=mock_db,
                tenant_id=str(uuid4()),
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["tasks"]) == 2
            assert result["tasks"][0]["name"] == "Task 1"
            assert result["tasks"][1]["is_active"] is False

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_list_scheduled_tasks

        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.agents.internal_tools.scheduler_tools.SchedulerService") as mock_service:
            mock_service.side_effect = Exception("Database error")

            result = await internal_list_scheduled_tasks(
                db=mock_db,
                tenant_id=str(uuid4()),
            )

            assert result["success"] is False
            assert "error" in result


class TestInternalDeleteScheduledTask:
    """Tests for internal_delete_scheduled_task function."""

    @pytest.mark.asyncio
    async def test_deletes_task_successfully(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_delete_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = str(uuid4())

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.delete_task = AsyncMock(return_value=None)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_delete_scheduled_task(
                db=mock_db,
                task_id=task_id,
            )

            assert result["success"] is True
            assert "deleted successfully" in result["message"]
            mock_scheduler_service.delete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_delete_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.delete_task = AsyncMock(side_effect=Exception("Task not found"))

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_delete_scheduled_task(
                db=mock_db,
                task_id=str(uuid4()),
            )

            assert result["success"] is False
            assert "Task not found" in result["error"]


class TestInternalToggleScheduledTask:
    """Tests for internal_toggle_scheduled_task function."""

    @pytest.mark.asyncio
    async def test_activates_task_successfully(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_toggle_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.is_active = True

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.toggle_task = AsyncMock(return_value=mock_task)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_toggle_scheduled_task(
                db=mock_db,
                task_id=str(task_id),
            )

            assert result["success"] is True
            assert result["is_active"] is True
            assert "activated" in result["message"]

    @pytest.mark.asyncio
    async def test_deactivates_task_successfully(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_toggle_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)
        task_id = uuid4()

        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.is_active = False

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.toggle_task = AsyncMock(return_value=mock_task)

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_toggle_scheduled_task(
                db=mock_db,
                task_id=str(task_id),
            )

            assert result["success"] is True
            assert result["is_active"] is False
            assert "deactivated" in result["message"]

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.agents.internal_tools.scheduler_tools import internal_toggle_scheduled_task

        mock_db = AsyncMock(spec=AsyncSession)

        mock_scheduler_service = MagicMock()
        mock_scheduler_service.toggle_task = AsyncMock(side_effect=Exception("Task not found"))

        with patch(
            "src.services.agents.internal_tools.scheduler_tools.SchedulerService",
            return_value=mock_scheduler_service,
        ):
            result = await internal_toggle_scheduled_task(
                db=mock_db,
                task_id=str(uuid4()),
            )

            assert result["success"] is False
            assert "Task not found" in result["error"]
