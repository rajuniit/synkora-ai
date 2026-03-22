"""Tests for file_tasks.py.

Note: These tests focus on testing the task logic by mocking the deferred imports
and database interactions. The actual Celery task execution is tested with mocks.
"""

import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def mock_modules():
    """Setup mock modules for testing and clean up after.

    This fixture mocks modules that may not exist or need to be isolated
    for testing file_tasks. It properly restores sys.modules after each test.
    """
    original_modules = {}
    mock_module_names = [
        "src.models.file",
        "src.services.storage.file_processor",
        "src.services.knowledge_base.embedding_service",
        "src.services.export",
        "src.services.export.export_service",
        "src.services.reports",
        "src.services.reports.report_generator",
        "src.services.backup",
        "src.services.backup.backup_service",
        "src.services.storage.compression_service",
        "src.services.security.virus_scanner",
    ]

    # Save original modules and install mocks
    for name in mock_module_names:
        original_modules[name] = sys.modules.get(name)
        sys.modules[name] = MagicMock()

    # Setup specific mock attributes needed by file_tasks
    sys.modules["src.models.file"].File = MagicMock()

    yield

    # Restore original modules
    for name, original in original_modules.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


@pytest.fixture
def mock_s3_storage():
    """Mock S3StorageService for tests that need it."""
    with patch("src.services.storage.s3_storage.S3StorageService") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock()
    db.query = Mock()
    db.commit = Mock()
    db.close = Mock()
    db.rollback = Mock()
    db.delete = Mock()
    db.add = Mock()
    return db


@pytest.fixture
def sample_file():
    """Create a sample file mock."""
    file = Mock()
    file.id = uuid4()
    file.storage_path = "uploads/test-file.pdf"
    file.processing_status = "pending"
    file.processed_at = None
    file.virus_scan_status = None
    file.virus_scan_date = None
    file.is_temporary = True
    file.created_at = datetime.now(UTC) - timedelta(hours=48)
    return file


class TestProcessFileUploadTask:
    """Tests for process_file_upload_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import process_file_upload_task

        assert process_file_upload_task is not None
        assert hasattr(process_file_upload_task, "name")
        assert process_file_upload_task.name == "process_file_upload_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import process_file_upload_task

        assert process_file_upload_task.max_retries == 3


class TestGenerateDocumentEmbeddingsTask:
    """Tests for generate_document_embeddings_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import generate_document_embeddings_task

        assert generate_document_embeddings_task is not None
        assert generate_document_embeddings_task.name == "generate_document_embeddings_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import generate_document_embeddings_task

        assert generate_document_embeddings_task.max_retries == 3


class TestExportDataTask:
    """Tests for export_data_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import export_data_task

        assert export_data_task is not None
        assert export_data_task.name == "export_data_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import export_data_task

        assert export_data_task.max_retries == 2


class TestGenerateReportTask:
    """Tests for generate_report_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import generate_report_task

        assert generate_report_task is not None
        assert generate_report_task.name == "generate_report_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import generate_report_task

        assert generate_report_task.max_retries == 2


class TestCleanupTempFilesTask:
    """Tests for cleanup_temp_files_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import cleanup_temp_files_task

        assert cleanup_temp_files_task is not None
        assert cleanup_temp_files_task.name == "cleanup_temp_files_task"


class TestBackupDatabaseTask:
    """Tests for backup_database_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import backup_database_task

        assert backup_database_task is not None
        assert backup_database_task.name == "backup_database_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import backup_database_task

        assert backup_database_task.max_retries == 1


class TestCompressFilesTask:
    """Tests for compress_files_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import compress_files_task

        assert compress_files_task is not None
        assert compress_files_task.name == "compress_files_task"


class TestScanFileForVirusesTask:
    """Tests for scan_file_for_viruses_task task structure."""

    def test_task_is_defined(self):
        """Test that the task is properly defined."""
        from src.tasks.file_tasks import scan_file_for_viruses_task

        assert scan_file_for_viruses_task is not None
        assert scan_file_for_viruses_task.name == "scan_file_for_viruses_task"

    def test_task_has_retry_config(self):
        """Test that task has retry configuration."""
        from src.tasks.file_tasks import scan_file_for_viruses_task

        assert scan_file_for_viruses_task.max_retries == 2


class TestTaskDatabasePatterns:
    """Test common database patterns in tasks."""

    def test_session_local_import(self):
        """Test that SessionLocal is importable from tasks module."""
        from src.tasks.file_tasks import SessionLocal

        # Just verify it's importable
        assert SessionLocal is not None


class TestTaskIntegration:
    """Integration-style tests that verify task behavior with mocked dependencies."""

    @patch("src.tasks.file_tasks.SessionLocal")
    @patch("src.services.storage.s3_storage.S3StorageService")
    def test_cleanup_temp_files_returns_result(self, mock_s3_class, mock_session_local, mock_db, sample_file):
        """Test cleanup_temp_files_task returns proper result structure."""
        from src.tasks.file_tasks import cleanup_temp_files_task

        mock_session_local.return_value = mock_db

        # Setup mock File class in the module
        mock_file_class = Mock()
        mock_file_module = sys.modules["src.models.file"]
        mock_file_module.File = mock_file_class

        # Setup query to return sample files
        file_query = Mock()
        file_query.filter.return_value.filter.return_value.all.return_value = [sample_file]
        mock_db.query.return_value = file_query

        # Setup S3Storage mock
        mock_s3_instance = Mock()
        mock_s3_instance.delete_file.return_value = True
        mock_s3_class.return_value = mock_s3_instance

        result = cleanup_temp_files_task(hours_old=24)

        assert "success" in result
        assert "deleted_count" in result or "error" in result
        mock_db.close.assert_called_once()

    @patch("src.tasks.file_tasks.SessionLocal")
    def test_cleanup_handles_exception_gracefully(self, mock_session_local, mock_db):
        """Test cleanup task handles database exceptions."""
        from src.tasks.file_tasks import cleanup_temp_files_task

        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("Database connection failed")

        result = cleanup_temp_files_task(hours_old=24)

        assert result["success"] is False
        assert "error" in result
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
