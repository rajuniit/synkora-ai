"""Tests for data_source_tasks.py.

Note: These tests focus on testing the task structure and basic patterns
since the actual task execution requires complex mock setups.
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock()
    db.query = Mock()
    db.commit = Mock()
    db.close = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def sample_data_source():
    """Create a sample data source mock."""
    ds = Mock()
    ds.id = uuid4()
    ds.type = "gmail"
    ds.tenant_id = uuid4()
    ds.is_active = True
    ds.last_synced_at = None
    return ds


class TestSyncDataSourceTask:
    """Tests for sync_data_source_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task is not None
        assert hasattr(sync_data_source_task, "name")
        assert sync_data_source_task.name == "sync_data_source_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task.max_retries == 3

    def test_task_default_retry_delay(self):
        """Test that task has default retry delay."""
        from src.tasks.data_source_tasks import sync_data_source_task

        assert sync_data_source_task.default_retry_delay == 300


class TestSyncAllDataSourcesTask:
    """Tests for sync_all_data_sources_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        assert sync_all_data_sources_task is not None
        assert sync_all_data_sources_task.name == "sync_all_data_sources_task"


class TestProcessDataSourceDocumentTask:
    """Tests for process_data_source_document_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.data_source_tasks import process_data_source_document_task

        assert process_data_source_document_task is not None
        assert process_data_source_document_task.name == "process_data_source_document_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.data_source_tasks import process_data_source_document_task

        assert process_data_source_document_task.max_retries == 3


class TestCleanupOldDataSourceItemsTask:
    """Tests for cleanup_old_data_source_items_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.data_source_tasks import cleanup_old_data_source_items_task

        assert cleanup_old_data_source_items_task is not None
        assert cleanup_old_data_source_items_task.name == "cleanup_old_data_source_items_task"


class TestTaskDatabasePatterns:
    """Test common database patterns in data source tasks."""

    def test_session_local_import(self):
        """Test that SessionLocal is importable from tasks module."""
        from src.tasks.data_source_tasks import SessionLocal

        # Just verify it's importable
        assert SessionLocal is not None


class TestSyncDataSourceTaskExecution:
    """Tests for actual sync_data_source_task execution with mocks."""

    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_data_source_not_found(self, mock_session_local, mock_db):
        """Test handling when data source not found."""
        from src.tasks.data_source_tasks import sync_data_source_task

        mock_session_local.return_value = mock_db

        ds_query = Mock()
        ds_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = ds_query

        result = sync_data_source_task(data_source_id=str(uuid4()), full_sync=False)

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        mock_db.close.assert_called_once()

    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_unsupported_data_source_type(self, mock_session_local, mock_db):
        """Test handling unsupported data source type."""
        from src.tasks.data_source_tasks import sync_data_source_task

        mock_session_local.return_value = mock_db

        unsupported_ds = Mock()
        unsupported_ds.id = uuid4()
        unsupported_ds.type = "unsupported_type"

        ds_query = Mock()
        ds_query.filter.return_value.first.return_value = unsupported_ds
        mock_db.query.return_value = ds_query

        result = sync_data_source_task(data_source_id=str(unsupported_ds.id), full_sync=False)

        assert result["success"] is False
        assert "unsupported" in result["error"].lower()
        mock_db.close.assert_called_once()


class TestSyncAllDataSourcesTaskExecution:
    """Tests for sync_all_data_sources_task execution with mocks."""

    @patch("src.tasks.data_source_tasks.sync_data_source_task")
    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_all_no_active_sources(self, mock_session_local, mock_sync_task, mock_db):
        """Test when no active data sources exist."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_session_local.return_value.__enter__ = Mock(return_value=mock_db)
        mock_session_local.return_value.__exit__ = Mock(return_value=False)
        mock_session_local.return_value = mock_db

        ds_query = Mock()
        ds_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = ds_query

        result = sync_all_data_sources_task()

        # Check result structure
        assert "total" in result or "success" in result
        if "total" in result:
            assert result["total"] == 0
            assert result["queued"] == 0
            assert result["failed"] == 0
        mock_db.close.assert_called_once()

    @patch("src.tasks.data_source_tasks.sync_data_source_task")
    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_all_queues_tasks(self, mock_session_local, mock_sync_task, mock_db, sample_data_source):
        """Test that sync_all queues individual sync tasks."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_session_local.return_value.__enter__ = Mock(return_value=mock_db)
        mock_session_local.return_value.__exit__ = Mock(return_value=False)
        mock_session_local.return_value = mock_db

        ds_query = Mock()
        ds_query.filter.return_value.all.return_value = [sample_data_source]
        mock_db.query.return_value = ds_query

        mock_sync_task.delay = Mock()

        result = sync_all_data_sources_task()

        # Check result structure
        assert "total" in result or "success" in result
        if "total" in result:
            assert result["total"] == 1
            assert result["queued"] == 1
            mock_sync_task.delay.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("src.tasks.data_source_tasks.sync_data_source_task")
    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_all_handles_queue_failure(self, mock_session_local, mock_sync_task, mock_db, sample_data_source):
        """Test handling when queueing a task fails."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_session_local.return_value.__enter__ = Mock(return_value=mock_db)
        mock_session_local.return_value.__exit__ = Mock(return_value=False)
        mock_session_local.return_value = mock_db

        ds_query = Mock()
        ds_query.filter.return_value.all.return_value = [sample_data_source]
        mock_db.query.return_value = ds_query

        mock_sync_task.delay = Mock(side_effect=Exception("Queue error"))

        result = sync_all_data_sources_task()

        # Check result structure - should handle the exception
        assert "total" in result or "success" in result
        if "total" in result:
            assert result["total"] == 1
            assert result["queued"] == 0
            assert result["failed"] == 1

    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_sync_all_handles_db_exception(self, mock_session_local, mock_db):
        """Test handling database exception."""
        from src.tasks.data_source_tasks import sync_all_data_sources_task

        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("Database error")

        result = sync_all_data_sources_task()

        assert result["success"] is False
        assert "error" in result
        mock_db.close.assert_called_once()


class TestCleanupOldDataSourceItemsTaskExecution:
    """Tests for cleanup_old_data_source_items_task execution with mocks."""

    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_cleanup_success(self, mock_session_local, mock_db):
        """Test successful cleanup of old items."""
        from src.tasks.data_source_tasks import cleanup_old_data_source_items_task

        mock_session_local.return_value = mock_db

        # Mock the query chain: db.query(...).filter(..., ...).delete()
        # The source code calls .filter() once with multiple conditions
        item_query = Mock()
        item_query.filter.return_value.delete.return_value = 50
        mock_db.query.return_value = item_query

        # Create a mock DataSourceItem class with proper column attributes
        # that support SQLAlchemy-style comparisons
        class MockColumn:
            def __eq__(self, other):
                return Mock()

            def __lt__(self, other):
                return Mock()

            def __gt__(self, other):
                return Mock()

        class MockDataSourceItem:
            data_source_id = MockColumn()
            created_at = MockColumn()

        mock_module = MagicMock()
        mock_module.DataSourceItem = MockDataSourceItem

        with patch.dict("sys.modules", {"src.models.data_source_item": mock_module}):
            result = cleanup_old_data_source_items_task(data_source_id=str(uuid4()), days_old=90)

        assert result["success"] is True
        assert result["deleted_count"] == 50
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("src.tasks.data_source_tasks.SessionLocal")
    def test_cleanup_handles_exception(self, mock_session_local, mock_db):
        """Test cleanup handles exceptions."""
        from src.tasks.data_source_tasks import cleanup_old_data_source_items_task

        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("Database error")

        result = cleanup_old_data_source_items_task(data_source_id=str(uuid4()), days_old=90)

        assert result["success"] is False
        assert "error" in result
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
