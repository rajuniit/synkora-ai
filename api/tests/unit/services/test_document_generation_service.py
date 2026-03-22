"""Tests for DocumentGenerationService."""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# Provide real stub classes for types used in isinstance() checks inside the service
class _FakeSpacer:
    def __init__(self, *args, **kwargs):
        pass


class _FakeParagraph:
    def __init__(self, *args, **kwargs):
        pass


class _FakePreformatted:
    def __init__(self, *args, **kwargs):
        pass


class _FakeHRFlowable:
    def __init__(self, *args, **kwargs):
        pass


class _FakeTable:
    def __init__(self, *args, **kwargs):
        pass


_platypus_mock = MagicMock()
_platypus_mock.Spacer = _FakeSpacer
_platypus_mock.Paragraph = _FakeParagraph
_platypus_mock.Preformatted = _FakePreformatted
_platypus_mock.HRFlowable = _FakeHRFlowable
_platypus_mock.Table = _FakeTable

# Mock reportlab and pptx before importing the service so CI doesn't need them installed
for _mod in [
    "reportlab",
    "reportlab.lib",
    "reportlab.lib.colors",
    "reportlab.lib.pagesizes",
    "reportlab.lib.styles",
    "reportlab.lib.units",
    "pptx",
    "pptx.util",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

if "reportlab.platypus" not in sys.modules:
    sys.modules["reportlab.platypus"] = _platypus_mock

from src.services.document_generation_service import DocumentGenerationService  # noqa: E402


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def tenant_id():
    """Create test tenant ID."""
    return uuid4()


@pytest.fixture
def document_service(mock_db, tenant_id):
    """Create DocumentGenerationService instance."""
    with patch("src.services.document_generation_service.S3StorageService"):
        service = DocumentGenerationService(mock_db, tenant_id)
        service.storage = Mock()
        return service


class TestInlineMarkup:
    """Tests for _inline_markup method."""

    def test_clean_bold(self, document_service):
        """Test converting bold markdown."""
        text = "This is **bold** text"
        result = document_service._inline_markup(text)

        assert "<b>bold</b>" in result
        assert "**" not in result

    def test_clean_italic(self, document_service):
        """Test converting italic markdown."""
        text = "This is *italic* text"
        result = document_service._inline_markup(text)

        assert "<i>italic</i>" in result

    def test_clean_code(self, document_service):
        """Test converting inline code."""
        text = "This is `code` text"
        result = document_service._inline_markup(text)

        assert 'name="Courier"' in result
        assert "`" not in result

    def test_strips_html_tags(self, document_service):
        """Test that HTML tags are stripped."""
        text = "Hello <b>world</b>"
        result = document_service._inline_markup(text)

        assert "<b>world</b>" not in result or "world" in result


class TestGeneratePDF:
    """Tests for generate_pdf method."""

    async def test_generate_pdf_success(self, document_service):
        """Test successfully generating PDF."""
        content = "# Test Document\n\nThis is test content."

        # Mock storage upload
        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/test.pdf",
                "url": "https://s3.amazonaws.com/bucket/test.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/test.pdf")

        result = await document_service.generate_pdf(
            content=content,
            title="Test Document",
            filename="test.pdf",
        )

        assert result["success"] is True
        assert result["format"] == "pdf"
        assert result["file_name"] == "test.pdf"
        assert "file_path" in result
        assert "download_url" in result
        document_service.storage.upload_file.assert_called_once()

    async def test_generate_pdf_with_auto_filename(self, document_service):
        """Test generating PDF with auto-generated filename."""
        content = "Test content"

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/auto.pdf",
                "url": "https://s3.amazonaws.com/bucket/auto.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/auto.pdf")

        result = await document_service.generate_pdf(
            content=content,
            title="Auto Title",
        )

        assert result["success"] is True
        assert result["file_name"].endswith(".pdf")
        assert "Auto_Title" in result["file_name"]

    async def test_generate_pdf_with_metadata(self, document_service):
        """Test generating PDF with metadata."""
        content = "Test content"

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/test.pdf",
                "url": "https://s3.amazonaws.com/bucket/test.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/test.pdf")

        result = await document_service.generate_pdf(
            content=content,
            title="Test",
            author="Test Author",
            include_metadata=True,
        )

        assert result["success"] is True

    async def test_generate_pdf_with_code_blocks(self, document_service):
        """Test generating PDF with code blocks."""
        content = """# Code Example

```python
def hello():
    print("Hello, World!")
```

Regular text after code."""

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/code.pdf",
                "url": "https://s3.amazonaws.com/bucket/code.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/code.pdf")

        result = await document_service.generate_pdf(
            content=content,
            title="Code Example",
        )

        assert result["success"] is True

    async def test_generate_pdf_empty_content(self, document_service):
        """Test generating PDF with empty content."""
        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/empty.pdf",
                "url": "https://s3.amazonaws.com/bucket/empty.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/empty.pdf")

        result = await document_service.generate_pdf(
            content="",
            title="Empty",
        )

        assert result["success"] is True

    async def test_generate_pdf_storage_error(self, document_service):
        """Test handling storage error."""
        content = "Test content"

        document_service.storage.upload_file = Mock(side_effect=Exception("Storage error"))

        result = await document_service.generate_pdf(
            content=content,
            title="Test",
        )

        assert result["success"] is False
        assert "error" in result
        assert "Storage error" in result["error"]

    async def test_generate_pdf_without_pdf_extension(self, document_service):
        """Test adding .pdf extension if missing."""
        content = "Test"

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/test.pdf",
                "url": "https://s3.amazonaws.com/bucket/test.pdf",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/test.pdf")

        result = await document_service.generate_pdf(
            content=content,
            filename="test",  # No .pdf extension
        )

        assert result["success"] is True
        assert result["file_name"] == "test.pdf"


class TestGeneratePowerPoint:
    """Tests for generate_powerpoint method."""

    async def test_generate_powerpoint_success(self, document_service):
        """Test successfully generating PowerPoint."""
        slides_content = [
            {"title": "Slide 1", "content": "Content 1"},
            {"title": "Slide 2", "bullet_points": ["Point 1", "Point 2"]},
        ]

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/test.pptx",
                "url": "https://s3.amazonaws.com/bucket/test.pptx",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/test.pptx")

        result = await document_service.generate_powerpoint(
            slides_content=slides_content,
            title="Test Presentation",
            filename="test.pptx",
        )

        assert result["success"] is True
        assert result["format"] == "powerpoint"
        assert result["file_name"] == "test.pptx"
        assert "slides" in result
        document_service.storage.upload_file.assert_called_once()

    async def test_generate_powerpoint_with_bullet_points(self, document_service):
        """Test generating PowerPoint with bullet points."""
        slides_content = [
            {
                "title": "Features",
                "bullet_points": [
                    "Feature 1",
                    "Feature 2",
                    "Feature 3",
                ],
            },
        ]

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/bullets.pptx",
                "url": "https://s3.amazonaws.com/bucket/bullets.pptx",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/bullets.pptx")

        result = await document_service.generate_powerpoint(
            slides_content=slides_content,
            title="Features",
        )

        assert result["success"] is True

    async def test_generate_powerpoint_with_auto_filename(self, document_service):
        """Test generating PowerPoint with auto-generated filename."""
        slides_content = [{"title": "Slide 1", "content": "Content"}]

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/auto.pptx",
                "url": "https://s3.amazonaws.com/bucket/auto.pptx",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/auto.pptx")

        result = await document_service.generate_powerpoint(
            slides_content=slides_content,
            title="Auto Presentation",
        )

        assert result["success"] is True
        assert result["file_name"].endswith(".pptx")
        assert "Auto_Presentation" in result["file_name"]

    async def test_generate_powerpoint_storage_error(self, document_service):
        """Test handling storage error."""
        slides_content = [{"title": "Slide", "content": "Content"}]

        document_service.storage.upload_file = Mock(side_effect=Exception("Storage error"))

        result = await document_service.generate_powerpoint(
            slides_content=slides_content,
            title="Test",
        )

        assert result["success"] is False
        assert "error" in result

    async def test_generate_powerpoint_without_pptx_extension(self, document_service):
        """Test adding .pptx extension if missing."""
        slides_content = [{"title": "Test", "content": "Content"}]

        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/test.pptx",
                "url": "https://s3.amazonaws.com/bucket/test.pptx",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/test.pptx")

        result = await document_service.generate_powerpoint(
            slides_content=slides_content,
            filename="test",  # No .pptx extension
        )

        assert result["success"] is True
        assert result["file_name"] == "test.pptx"

    async def test_generate_powerpoint_empty_slides(self, document_service):
        """Test generating PowerPoint with empty slides list."""
        document_service.storage.upload_file = Mock(
            return_value={
                "key": "documents/test/empty.pptx",
                "url": "https://s3.amazonaws.com/bucket/empty.pptx",
            }
        )
        document_service.storage.generate_presigned_url = Mock(return_value="https://signed-url.com/empty.pptx")

        result = await document_service.generate_powerpoint(
            slides_content=[],
            title="Empty",
        )

        assert result["success"] is True
        # Should have at least a title slide
        assert "slides" in result


class TestGenerateGoogleDoc:
    """Tests for generate_google_doc method."""

    async def test_generate_google_doc_not_implemented(self, document_service):
        """Test Google Doc generation returns setup message."""
        result = await document_service.generate_google_doc(
            content="Test content",
            title="Test Doc",
        )

        assert result["success"] is False
        assert "setup_required" in result
        assert result["setup_required"] is True
        assert "OAuth setup" in result["message"]


class TestGenerateGoogleSheet:
    """Tests for generate_google_sheet method."""

    async def test_generate_google_sheet_not_implemented(self, document_service):
        """Test Google Sheet generation returns setup message."""
        data = [["Header 1", "Header 2"], ["Value 1", "Value 2"]]

        result = await document_service.generate_google_sheet(
            data=data,
            title="Test Sheet",
        )

        assert result["success"] is False
        assert "setup_required" in result
        assert result["setup_required"] is True
        assert "OAuth setup" in result["message"]
