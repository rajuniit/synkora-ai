import sys
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# Create a mock magic module to be used in tests
class MockMagic:
    @staticmethod
    def from_buffer(data, mime=False):
        # Default to text/plain for tests
        return "text/plain"


# Pre-install mock magic in sys.modules for tests that need it
mock_magic_module = MockMagic()


class TestAttachmentService:
    @pytest.fixture
    def mock_magic(self):
        """Mock the magic module that's imported inside upload_attachment."""
        mock_magic = MagicMock()
        mock_magic.from_buffer.return_value = "text/plain"
        with patch.dict(sys.modules, {"magic": mock_magic}):
            yield mock_magic

    @pytest.fixture
    def mock_s3(self):
        with patch("src.services.chat.attachment_service.S3StorageService") as MockS3:
            s3_instance = MockS3.return_value
            s3_instance.upload_file.return_value = {"url": "http://s3/file"}
            s3_instance.generate_presigned_url.return_value = "http://presigned/file"
            yield s3_instance

    @pytest.fixture
    def service(self, mock_s3, mock_magic):
        from src.services.chat.attachment_service import AttachmentService

        return AttachmentService()

    @pytest.mark.asyncio
    async def test_upload_attachment_bytes_success(self, service, mock_s3):
        content = b"test content"
        result = await service.upload_attachment(
            file_content=content,
            filename="test.txt",
            content_type="text/plain",
            tenant_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert result["file_name"] == "test.txt"
        assert result["file_size"] == len(content)
        assert result["extracted_text"] == "test content"
        mock_s3.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_attachment_file_obj_success(self, service, mock_s3):
        content = b"test content"
        file_obj = BytesIO(content)

        result = await service.upload_attachment(
            file_content=file_obj,
            filename="test.txt",
            content_type="text/plain",
            tenant_id=uuid4(),
            conversation_id=uuid4(),
        )

        assert result["file_name"] == "test.txt"
        assert result["file_size"] == len(content)
        assert result["extracted_text"] == "test content"
        mock_s3.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_attachment_invalid_type(self, mock_s3, mock_magic):
        # Service now uses magic library to detect actual file type
        # Mock magic to return an unsupported type
        mock_magic.from_buffer.return_value = "application/x-msdownload"
        from src.services.chat.attachment_service import AttachmentService

        service = AttachmentService()
        with pytest.raises(ValueError, match="Unsupported file type"):
            await service.upload_attachment(
                file_content=b"test",
                filename="test.exe",
                content_type="application/x-msdownload",
                tenant_id=uuid4(),
                conversation_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_upload_attachment_too_large(self, service):
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            await service.upload_attachment(
                file_content=large_content,
                filename="large.txt",
                content_type="text/plain",
                tenant_id=uuid4(),
                conversation_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_extract_text_markdown(self, service, mock_s3):
        content = b"# Heading"
        result = await service.upload_attachment(
            file_content=content,
            filename="test.md",
            content_type="text/markdown",
            tenant_id=uuid4(),
            conversation_id=uuid4(),
        )
        assert result["extracted_text"] == "# Heading"

    @pytest.mark.asyncio
    async def test_extract_text_pdf(self, mock_s3, mock_magic):
        # PDF extraction is now supported; test that it attempts extraction
        # with invalid PDF content, extraction will fail gracefully
        content = b"not a valid pdf"
        mock_magic.from_buffer.return_value = "application/pdf"
        from src.services.chat.attachment_service import AttachmentService

        service = AttachmentService()
        result = await service.upload_attachment(
            file_content=content,
            filename="test.pdf",
            content_type="application/pdf",
            tenant_id=uuid4(),
            conversation_id=uuid4(),
        )
        # With invalid PDF content, extraction returns None
        assert result["extracted_text"] is None

    def test_validate_attachments_success(self, service):
        attachments = [{"file_size": 100} for _ in range(3)]
        service.validate_attachments(attachments)

    def test_validate_attachments_too_many(self, service):
        attachments = [{"file_size": 100} for _ in range(6)]
        with pytest.raises(ValueError, match="Too many attachments"):
            service.validate_attachments(attachments)

    def test_get_attachment_context(self, service):
        attachments = [
            {"file_name": "a.txt", "file_type": "text/plain", "file_size": 10, "extracted_text": "content A"},
            {"file_name": "b.pdf", "file_type": "application/pdf", "file_size": 20},
        ]
        context = service.get_attachment_context(attachments)
        assert "a.txt" in context
        assert "content A" in context
        assert "b.pdf" in context

    def test_get_attachment_context_truncated(self, service):
        long_text = "x" * 6000
        attachments = [{"file_name": "a.txt", "file_type": "text/plain", "file_size": 10, "extracted_text": long_text}]
        context = service.get_attachment_context(attachments)
        assert "truncated" in context
        assert len(context) < 6000

    def test_is_image_attachment(self, service):
        assert service.is_image_attachment({"file_type": "image/png"}) is True
        assert service.is_image_attachment({"file_type": "text/plain"}) is False

    def test_get_image_attachments(self, service):
        attachments = [{"file_type": "image/png"}, {"file_type": "text/plain"}]
        images = service.get_image_attachments(attachments)
        assert len(images) == 1
        assert images[0]["file_type"] == "image/png"
