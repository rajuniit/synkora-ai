"""Tests for documents controller."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.controllers.documents import router
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def client(mock_db_session, mock_tenant_id):
    app = FastAPI()
    app.include_router(router)

    # Mock dependencies
    async def mock_db():
        yield mock_db_session

    app.dependency_overrides[get_async_db] = mock_db
    app.dependency_overrides[get_current_tenant_id] = lambda: mock_tenant_id

    return TestClient(app), mock_db_session, mock_tenant_id


class TestStreamDocument:
    """Tests for streaming documents."""

    def test_stream_document_success(self, client):
        """Test successful document streaming."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"PDF content here"

            response = test_client.get("/api/documents/stream/path/to/document.pdf")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "application/pdf"
            assert response.headers["content-disposition"] == "inline"

    def test_stream_document_not_found(self, client):
        """Test streaming non-existent document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = None

            response = test_client.get("/api/documents/stream/path/to/nonexistent.pdf")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_document_docx(self, client):
        """Test streaming DOCX document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"DOCX content"

            response = test_client.get("/api/documents/stream/path/to/document.docx")

            assert response.status_code == status.HTTP_200_OK
            assert (
                response.headers["content-type"]
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    def test_stream_document_txt(self, client):
        """Test streaming TXT document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Plain text content"

            response = test_client.get("/api/documents/stream/path/to/document.txt")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"].startswith("text/plain")

    def test_stream_document_xlsx(self, client):
        """Test streaming XLSX document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Excel content"

            response = test_client.get("/api/documents/stream/path/to/spreadsheet.xlsx")

            assert response.status_code == status.HTTP_200_OK
            assert (
                response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def test_stream_document_csv(self, client):
        """Test streaming CSV document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"col1,col2\nval1,val2"

            response = test_client.get("/api/documents/stream/path/to/data.csv")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"].startswith("text/csv")

    def test_stream_document_md(self, client):
        """Test streaming Markdown document."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"# Heading\n\nContent"

            response = test_client.get("/api/documents/stream/path/to/readme.md")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"].startswith("text/markdown")

    def test_stream_document_unknown_type(self, client):
        """Test streaming document with unknown type."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Unknown content"

            response = test_client.get("/api/documents/stream/path/to/file.xyz")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "application/octet-stream"

    def test_stream_document_error(self, client):
        """Test streaming document with S3 error."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.side_effect = Exception("S3 error")

            response = test_client.get("/api/documents/stream/path/to/document.pdf")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_stream_document_nested_path(self, client):
        """Test streaming document with nested path."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Content"

            response = test_client.get("/api/documents/stream/tenant/kb-1/uploads/file.pdf")

            assert response.status_code == status.HTTP_200_OK
            mock_storage.download_file.assert_called_with("tenant/kb-1/uploads/file.pdf")

    def test_stream_document_cache_headers(self, client):
        """Test that streaming includes proper cache headers."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Content"

            response = test_client.get("/api/documents/stream/document.pdf")

            assert response.status_code == status.HTTP_200_OK
            assert "Cache-Control" in response.headers
            assert "public" in response.headers["Cache-Control"]

    def test_stream_document_cors_headers(self, client):
        """Test that streaming includes CORS headers."""
        test_client, mock_db, mock_tenant_id = client

        with (
            patch("src.controllers.documents.S3StorageService") as mock_s3,
            patch("src.controllers.documents._validate_s3_key_ownership", return_value=True),
        ):
            mock_storage = mock_s3.return_value
            mock_storage.download_file.return_value = b"Content"

            response = test_client.get("/api/documents/stream/document.pdf")

            assert response.status_code == status.HTTP_200_OK
            # CORS header should be present (value depends on env config)
            assert "Access-Control-Allow-Origin" in response.headers

    def test_stream_document_access_denied(self, client):
        """Test streaming document that doesn't belong to tenant."""
        test_client, mock_db, mock_tenant_id = client

        with patch("src.controllers.documents._validate_s3_key_ownership", return_value=False):
            response = test_client.get("/api/documents/stream/other/tenant/document.pdf")

            assert response.status_code == status.HTTP_404_NOT_FOUND
