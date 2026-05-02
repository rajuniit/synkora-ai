"""
Tests for google_drive_tools.py - Google Drive Tools

Tests the Google Drive integration including file operations,
folder operations, sharing, and Google Docs/Sheets operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSanitizeFileId:
    """Tests for _sanitize_file_id helper function."""

    def test_strips_trailing_punctuation(self):
        from src.services.agents.internal_tools.google_drive_tools import _sanitize_file_id

        assert _sanitize_file_id("abc123.") == "abc123"
        assert _sanitize_file_id("abc123,") == "abc123"
        assert _sanitize_file_id("abc123;") == "abc123"
        assert _sanitize_file_id("abc123!") == "abc123"
        assert _sanitize_file_id("abc123?") == "abc123"

    def test_strips_whitespace(self):
        from src.services.agents.internal_tools.google_drive_tools import _sanitize_file_id

        assert _sanitize_file_id("  abc123  ") == "abc123"

    def test_handles_empty_input(self):
        from src.services.agents.internal_tools.google_drive_tools import _sanitize_file_id

        assert _sanitize_file_id("") == ""

    def test_preserves_valid_ids(self):
        from src.services.agents.internal_tools.google_drive_tools import _sanitize_file_id

        assert (
            _sanitize_file_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms")
            == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
        )


class TestInternalGoogleDriveListFiles:
    """Tests for internal_google_drive_list_files function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_list_files

        result = await internal_google_drive_list_files(runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_files_successfully(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_list_files

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "files": [
                    {"id": "file-1", "name": "test.pdf"},
                    {"id": "file-2", "name": "report.docx"},
                ],
                "nextPageToken": None,
            }
        )
        mock_response.text = AsyncMock(return_value="")

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.internal_tools.google_drive_tools._get_google_drive_access_token",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_google_drive_list_files(
                runtime_context=MagicMock(),
            )

            assert result["total_returned"] == 2
            assert result["files"][0]["name"] == "test.pdf"


class TestInternalGoogleDriveGetFile:
    """Tests for internal_google_drive_get_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_get_file

        result = await internal_google_drive_get_file(file_id="file-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveDeleteFile:
    """Tests for internal_google_drive_delete_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_delete_file

        result = await internal_google_drive_delete_file(file_id="file-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_deletes_file_successfully(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_delete_file

        mock_response = AsyncMock()
        mock_response.status = 204

        mock_session = MagicMock()
        mock_session.delete.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.delete.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.internal_tools.google_drive_tools._get_google_drive_access_token",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_google_drive_delete_file(
                file_id="file-123",
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["file_id"] == "file-123"


class TestInternalGoogleDriveCreateFolder:
    """Tests for internal_google_drive_create_folder function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_create_folder

        result = await internal_google_drive_create_folder(name="New Folder", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveMoveFile:
    """Tests for internal_google_drive_move_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_move_file

        result = await internal_google_drive_move_file(
            file_id="file-123", new_parent_folder_id="folder-456", runtime_context=None
        )
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveShareFile:
    """Tests for internal_google_drive_share_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_share_file

        result = await internal_google_drive_share_file(
            file_id="file-123", email="user@example.com", runtime_context=None
        )
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveGetPermissions:
    """Tests for internal_google_drive_get_permissions function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_get_permissions

        result = await internal_google_drive_get_permissions(file_id="file-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveRemovePermission:
    """Tests for internal_google_drive_remove_permission function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_remove_permission

        result = await internal_google_drive_remove_permission(
            file_id="file-123", permission_id="perm-456", runtime_context=None
        )
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDocsCreateDocument:
    """Tests for internal_google_docs_create_document function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_docs_create_document

        result = await internal_google_docs_create_document(title="New Doc", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDocsGetContent:
    """Tests for internal_google_docs_get_content function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_docs_get_content

        result = await internal_google_docs_get_content(document_id="doc-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDocsAppendContent:
    """Tests for internal_google_docs_append_content function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_docs_append_content

        result = await internal_google_docs_append_content(
            document_id="doc-123", content="New content", runtime_context=None
        )
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleSheetsCreateSpreadsheet:
    """Tests for internal_google_sheets_create_spreadsheet function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_sheets_create_spreadsheet

        result = await internal_google_sheets_create_spreadsheet(title="New Sheet", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleSheetsReadRange:
    """Tests for internal_google_sheets_read_range function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_sheets_read_range

        result = await internal_google_sheets_read_range(spreadsheet_id="sheet-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleSheetsWriteRange:
    """Tests for internal_google_sheets_write_range function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_sheets_write_range

        result = await internal_google_sheets_write_range(
            spreadsheet_id="sheet-123", range_name="Sheet1!A1", values=[["Hello"]], runtime_context=None
        )
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveUploadFile:
    """Tests for internal_google_drive_upload_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_upload_file

        result = await internal_google_drive_upload_file(name="test.txt", content="Hello World", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveUpdateFile:
    """Tests for internal_google_drive_update_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_update_file

        result = await internal_google_drive_update_file(file_id="file-123", name="updated.txt", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]


class TestInternalGoogleDriveDownloadFile:
    """Tests for internal_google_drive_download_file function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_drive_tools import internal_google_drive_download_file

        result = await internal_google_drive_download_file(file_id="file-123", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context" in result["error"]
