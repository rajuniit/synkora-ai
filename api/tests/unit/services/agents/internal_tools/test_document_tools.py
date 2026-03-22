"""
Tests for document_tools.py - Document Generation Tools

Tests the document generation including PDF, PowerPoint,
Google Docs, and Google Sheets generation.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# Mock the pptx and reportlab modules to avoid import errors in test environment
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

sys.modules["pptx"] = MagicMock()
sys.modules["pptx.util"] = MagicMock()
sys.modules["reportlab"] = MagicMock()
sys.modules["reportlab.lib"] = MagicMock()
sys.modules["reportlab.lib.colors"] = MagicMock()
sys.modules["reportlab.lib.pagesizes"] = MagicMock()
sys.modules["reportlab.lib.styles"] = MagicMock()
sys.modules["reportlab.platypus"] = _platypus_mock


class TestInternalGeneratePdf:
    """Tests for internal_generate_pdf function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_runtime_context_is_none(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_pdf

        result = await internal_generate_pdf(content="Test content", runtime_context=None)

        assert result["success"] is False
        assert result["error"] == "Tenant ID not found in runtime context"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_tenant_id(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_pdf

        result = await internal_generate_pdf(content="Test content", runtime_context={})

        assert result["success"] is False
        assert result["error"] == "Tenant ID not found in runtime context"

    @pytest.mark.asyncio
    async def test_generates_pdf_with_dict_context(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_pdf

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_db = AsyncMock(spec=AsyncSession)
        mock_service = MagicMock()
        mock_service.generate_pdf = AsyncMock(
            return_value={"success": True, "file_path": "/path/to/file.pdf", "file_name": "test.pdf", "file_size": 1024}
        )

        # Create a mock async session factory that returns our mock db as async context manager
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "src.core.database.get_async_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "src.services.document_generation_service.DocumentGenerationService",
                return_value=mock_service,
            ) as mock_service_class,
        ):
            result = await internal_generate_pdf(
                content="Test content",
                title="Test Document",
                filename="test",
                author="Test Author",
                include_metadata=True,
                runtime_context={"tenant_id": tenant_id},
            )

            assert result["success"] is True
            mock_service_class.assert_called_once_with(mock_db, UUID(tenant_id))

    @pytest.mark.asyncio
    async def test_generates_pdf_with_object_context(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_pdf

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_db = AsyncMock(spec=AsyncSession)
        mock_service = MagicMock()
        mock_service.generate_pdf = AsyncMock(
            return_value={"success": True, "file_path": "/path/to/file.pdf", "file_name": "test.pdf", "file_size": 1024}
        )

        runtime_context_obj = MagicMock()
        runtime_context_obj.tenant_id = tenant_id

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "src.core.database.get_async_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "src.services.document_generation_service.DocumentGenerationService",
                return_value=mock_service,
            ) as mock_service_class,
        ):
            result = await internal_generate_pdf(
                content="Test content",
                runtime_context=runtime_context_obj,
            )

            assert result["success"] is True
            mock_service_class.assert_called_once_with(mock_db, UUID(tenant_id))


class TestInternalGeneratePowerpoint:
    """Tests for internal_generate_powerpoint function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_runtime_context_is_none(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_powerpoint

        result = await internal_generate_powerpoint(
            slides_content=[{"title": "Slide 1", "content": "Content"}], runtime_context=None
        )

        assert result["success"] is False
        assert result["error"] == "Tenant ID not found in runtime context"

    @pytest.mark.asyncio
    async def test_generates_powerpoint_with_dict_context(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_powerpoint

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_db = AsyncMock(spec=AsyncSession)
        mock_service = MagicMock()
        mock_service.generate_powerpoint = AsyncMock(
            return_value={
                "success": True,
                "file_path": "/path/to/file.pptx",
                "file_name": "presentation.pptx",
                "file_size": 2048,
                "slide_count": 2,
            }
        )

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "src.core.database.get_async_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "src.services.document_generation_service.DocumentGenerationService",
                return_value=mock_service,
            ) as mock_service_class,
        ):
            result = await internal_generate_powerpoint(
                slides_content=[{"title": "Intro", "bullet_points": ["Point 1"]}],
                title="Test Presentation",
                filename="presentation",
                runtime_context={"tenant_id": tenant_id},
            )

            assert result["success"] is True
            mock_service_class.assert_called_once_with(mock_db, UUID(tenant_id))


class TestInternalGenerateGoogleDoc:
    """Tests for internal_generate_google_doc function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_runtime_context_is_none(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_google_doc

        result = await internal_generate_google_doc(content="Test content", runtime_context=None)

        assert result["success"] is False
        assert result["error"] == "Tenant ID not found in runtime context"

    @pytest.mark.asyncio
    async def test_generates_google_doc_with_dict_context(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_google_doc

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_db = AsyncMock(spec=AsyncSession)
        mock_service = MagicMock()
        mock_service.generate_google_doc = AsyncMock(
            return_value={
                "success": True,
                "document_url": "https://docs.google.com/document/d/abc123",
                "document_id": "abc123",
            }
        )

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "src.core.database.get_async_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "src.services.document_generation_service.DocumentGenerationService",
                return_value=mock_service,
            ),
        ):
            result = await internal_generate_google_doc(
                content="Test content",
                title="Test Google Doc",
                share_with_emails=["user@example.com"],
                runtime_context={"tenant_id": tenant_id},
            )

            assert result["success"] is True


class TestInternalGenerateGoogleSheet:
    """Tests for internal_generate_google_sheet function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_runtime_context_is_none(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_google_sheet

        result = await internal_generate_google_sheet(data=[["Name", "Age"], ["John", 30]], runtime_context=None)

        assert result["success"] is False
        assert result["error"] == "Tenant ID not found in runtime context"

    @pytest.mark.asyncio
    async def test_generates_google_sheet_with_dict_context(self):
        from src.services.agents.internal_tools.document_tools import internal_generate_google_sheet

        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_db = AsyncMock(spec=AsyncSession)
        mock_service = MagicMock()
        mock_service.generate_google_sheet = AsyncMock(
            return_value={
                "success": True,
                "spreadsheet_url": "https://docs.google.com/spreadsheets/d/xyz789",
                "spreadsheet_id": "xyz789",
            }
        )

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "src.core.database.get_async_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "src.services.document_generation_service.DocumentGenerationService",
                return_value=mock_service,
            ),
        ):
            result = await internal_generate_google_sheet(
                data=[["Name", "Age"], ["John", 30]],
                title="Test Spreadsheet",
                sheet_name="Data",
                runtime_context={"tenant_id": tenant_id},
            )

            assert result["success"] is True
