"""
Tests for gmail_tools.py - Gmail Tools

Tests the Gmail integration for listing, sending, searching,
deleting emails, drafts, and managing labels.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock googleapiclient to avoid pyparsing dependency issues
sys.modules["googleapiclient"] = MagicMock()
sys.modules["googleapiclient.discovery"] = MagicMock()
sys.modules["googleapiclient.errors"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.auth"] = MagicMock()
sys.modules["google.auth.transport"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["google.oauth2.credentials"] = MagicMock()


class TestInternalGmailListEmails:
    """Tests for internal_gmail_list_emails function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_list_emails

        result = await internal_gmail_list_emails(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailSearchEmails:
    """Tests for internal_gmail_search_emails function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_search_emails

        result = await internal_gmail_search_emails(
            query="from:test@example.com",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailGetEmail:
    """Tests for internal_gmail_get_email function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_get_email

        result = await internal_gmail_get_email(
            message_id="msg-123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailDeleteEmail:
    """Tests for internal_gmail_delete_email function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_delete_email

        result = await internal_gmail_delete_email(
            message_id="msg-123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailBulkDelete:
    """Tests for internal_gmail_bulk_delete function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_bulk_delete

        result = await internal_gmail_bulk_delete(
            query="older_than:30d",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_query_or_message_ids(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_bulk_delete

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_bulk_delete(
                query=None,
                message_ids=None,
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "query" in result["error"] and "message_ids" in result["error"]


class TestInternalGmailSendEmail:
    """Tests for internal_gmail_send_email function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_email

        result = await internal_gmail_send_email(
            to="user@example.com",
            subject="Test",
            body="Hello",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_to(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_email

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_send_email(
                to="",
                subject="Test",
                body="Hello",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "'to' is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_subject(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_email

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_send_email(
                to="user@example.com",
                subject="",
                body="Hello",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Subject is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_body(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_email

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_send_email(
                to="user@example.com",
                subject="Test",
                body="",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Body is required" in result["error"]


class TestInternalGmailReply:
    """Tests for internal_gmail_reply function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_reply

        result = await internal_gmail_reply(
            message_id="msg-123",
            body="Thanks!",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_message_id(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_reply

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_reply(
                message_id="",
                body="Thanks!",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Message ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_body(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_reply

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_reply(
                message_id="msg-123",
                body="",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Reply body is required" in result["error"]


class TestInternalGmailForward:
    """Tests for internal_gmail_forward function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_forward

        result = await internal_gmail_forward(
            message_id="msg-123",
            to="user@example.com",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_message_id(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_forward

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_forward(
                message_id="",
                to="user@example.com",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Message ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_to(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_forward

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_forward(
                message_id="msg-123",
                to="",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "'to' is required" in result["error"]


class TestInternalGmailGetLabels:
    """Tests for internal_gmail_get_labels function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_get_labels

        result = await internal_gmail_get_labels(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailEmptyTrash:
    """Tests for internal_gmail_empty_trash function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_empty_trash

        result = await internal_gmail_empty_trash(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailEmptySpam:
    """Tests for internal_gmail_empty_spam function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_empty_spam

        result = await internal_gmail_empty_spam(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailCreateDraft:
    """Tests for internal_gmail_create_draft function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_create_draft

        result = await internal_gmail_create_draft(
            to="user@example.com",
            subject="Test",
            body="Draft content",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_to(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_create_draft

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_create_draft(
                to="",
                subject="Test",
                body="Content",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "'to' is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_subject(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_create_draft

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_create_draft(
                to="user@example.com",
                subject="",
                body="Content",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Subject is required" in result["error"]


class TestInternalGmailListDrafts:
    """Tests for internal_gmail_list_drafts function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_list_drafts

        result = await internal_gmail_list_drafts(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalGmailSendDraft:
    """Tests for internal_gmail_send_draft function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_draft

        result = await internal_gmail_send_draft(
            draft_id="draft-123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_draft_id(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_send_draft

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_send_draft(
                draft_id="",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Draft ID is required" in result["error"]


class TestInternalGmailDeleteDraft:
    """Tests for internal_gmail_delete_draft function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_delete_draft

        result = await internal_gmail_delete_draft(
            draft_id="draft-123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_draft_id(self):
        from src.services.agents.internal_tools.gmail_tools import internal_gmail_delete_draft

        mock_service = MagicMock()

        with patch(
            "src.services.agents.internal_tools.gmail_tools._get_gmail_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_gmail_delete_draft(
                draft_id="",
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "Draft ID is required" in result["error"]


class TestCreateMessage:
    """Tests for _create_message helper function."""

    def test_creates_plain_text_message(self):
        from src.services.agents.internal_tools.gmail_tools import _create_message

        result = _create_message(
            to="user@example.com",
            subject="Test Subject",
            body="Hello World",
        )

        assert "raw" in result
        assert isinstance(result["raw"], str)
        assert "threadId" not in result

    def test_creates_html_message(self):
        from src.services.agents.internal_tools.gmail_tools import _create_message

        result = _create_message(
            to="user@example.com",
            subject="Test Subject",
            body="<h1>Hello</h1>",
            html=True,
        )

        assert "raw" in result

    def test_includes_thread_id(self):
        from src.services.agents.internal_tools.gmail_tools import _create_message

        result = _create_message(
            to="user@example.com",
            subject="Re: Test",
            body="Reply",
            thread_id="thread-123",
        )

        assert result["threadId"] == "thread-123"

    def test_includes_in_reply_to(self):
        from src.services.agents.internal_tools.gmail_tools import _create_message

        result = _create_message(
            to="user@example.com",
            subject="Re: Test",
            body="Reply",
            in_reply_to="<msg-id@gmail.com>",
        )

        assert "raw" in result
