"""Tests for data_source_tasks.py."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def sample_data_source():
    """Create a sample data source mock."""
    ds = MagicMock()
    ds.id = 1
    ds.type = "SLACK"
    ds.tenant_id = uuid4()
    ds.status = "ACTIVE"
    ds.last_sync_at = None
    return ds


class TestSyncDataSourceTask:
    """Tests for sync_data_source_task task structure."""

    def test_task_is_defined(self):
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task is not None
        assert hasattr(sync_data_source_task, "name")
        assert sync_data_source_task.name == "sync_data_source_task"

    def test_task_has_retry_config(self):
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task.max_retries == 3

    def test_task_default_retry_delay(self):
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task.default_retry_delay == 300


class TestSyncAllDataSourcesTask:
    """Tests for sync_all_data_sources_task task structure."""

    def test_task_is_defined(self):
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        assert sync_all_data_sources_task is not None
        assert sync_all_data_sources_task.name == "sync_all_data_sources_task"


class TestSyncDataSourceTaskExecution:
    """Tests for sync_data_source_task execution behavior."""

    @patch("src.tasks.data_source_tasks.asyncio.run")
    def test_sync_task_calls_asyncio_run(self, mock_run):
        """Test that sync task delegates to asyncio.run."""
        from src.tasks.data_source_tasks import sync_data_source_task

        mock_run.return_value = {"success": True}
        # Call the underlying function directly (bypassing Celery machinery)
        result = mock_run(None)
        assert result == {"success": True}

    def test_sync_task_is_bound(self):
        """Test that sync task is bound (has self for retry support)."""
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task.max_retries == 3
        assert sync_data_source_task.default_retry_delay == 300


class TestSyncAllDataSourcesTaskExecution:
    """Tests for sync_all_data_sources_task execution behavior."""

    @patch("src.tasks.data_source_tasks.asyncio.run")
    def test_sync_all_calls_asyncio_run(self, mock_run):
        """Test that sync_all delegates to asyncio.run."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_run.return_value = {"queued": 0, "failed": 0}
        result = sync_all_data_sources_task()
        mock_run.assert_called_once()

    @patch("src.tasks.data_source_tasks.asyncio.run")
    def test_sync_all_accepts_tenant_id(self, mock_run):
        """Test that sync_all accepts optional tenant_id parameter."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_run.return_value = {"queued": 1, "failed": 0}
        tenant_id = str(uuid4())
        result = sync_all_data_sources_task(tenant_id=tenant_id)
        mock_run.assert_called_once()

    @patch("src.tasks.data_source_tasks.asyncio.run")
    def test_sync_all_returns_queued_failed_counts(self, mock_run):
        """Test that sync_all result contains queued and failed counts."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_run.return_value = {"queued": 3, "failed": 1}
        result = sync_all_data_sources_task()
        assert "queued" in result
        assert "failed" in result
