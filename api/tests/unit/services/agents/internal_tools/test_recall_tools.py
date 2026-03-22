"""
Tests for recall_tools.py - Recall.ai Meeting Bot Tools

Tests the meeting bot capabilities including sending bots to meetings,
retrieving transcripts and recordings, and managing bot lifecycle.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetRecallService:
    """Tests for _get_recall_service helper function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_runtime_context(self):
        from src.services.agents.internal_tools.recall_tools import _get_recall_service

        result = await _get_recall_service(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_without_api_key(self):
        from src.services.agents.internal_tools.recall_tools import _get_recall_service

        mock_resolver = MagicMock()
        mock_resolver.get_recall_credentials = AsyncMock(return_value=(None, None, None))

        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            result = await _get_recall_service({"agent_id": "test"})
            assert result is None


class TestInternalRecallSendBot:
    """Tests for internal_recall_send_bot function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_send_bot

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_send_bot(
                meeting_url="https://zoom.us/j/123456",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_validates_join_at_format(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_send_bot

        mock_service = AsyncMock()

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_send_bot(
                meeting_url="https://zoom.us/j/123456",
                join_at="invalid-date-format",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "Invalid join_at format" in result["error"]

    @pytest.mark.asyncio
    async def test_sends_bot_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_send_bot

        mock_service = AsyncMock()
        mock_service.send_bot_to_meeting = AsyncMock(
            return_value={
                "success": True,
                "data": {"bot_id": "bot-123", "status": "joining"},
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_send_bot(
                meeting_url="https://zoom.us/j/123456",
                bot_name="Test Bot",
                runtime_context={"agent_id": "test-agent"},
            )

            assert result["success"] is True
            mock_service.send_bot_to_meeting.assert_called_once()


class TestInternalRecallGetBotStatus:
    """Tests for internal_recall_get_bot_status function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_bot_status

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_get_bot_status(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_status_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_bot_status

        mock_service = AsyncMock()
        mock_service.get_bot = AsyncMock(
            return_value={
                "success": True,
                "data": {"bot_id": "bot-123", "status": "in_call_recording"},
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_get_bot_status(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_service.get_bot.assert_called_once_with("bot-123")


class TestInternalRecallListBots:
    """Tests for internal_recall_list_bots function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_list_bots

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_list_bots(
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_lists_bots_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_list_bots

        mock_service = AsyncMock()
        mock_service.list_bots = AsyncMock(
            return_value={
                "success": True,
                "data": {
                    "bots": [
                        {"bot_id": "bot-1", "status": "done"},
                        {"bot_id": "bot-2", "status": "in_call"},
                    ]
                },
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_list_bots(
                status="done",
                limit=10,
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_service.list_bots.assert_called_once_with(status="done", limit=10)


class TestInternalRecallGetTranscript:
    """Tests for internal_recall_get_transcript function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_transcript

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_get_transcript(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_gets_transcript_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_transcript

        mock_service = AsyncMock()
        mock_service.get_transcript = AsyncMock(
            return_value={
                "success": True,
                "data": {
                    "full_text": "Hello everyone. Let's start the meeting.",
                    "segments": [{"speaker": "Alice", "text": "Hello everyone."}],
                },
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_get_transcript(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_service.get_transcript.assert_called_once_with("bot-123")


class TestInternalRecallGetRecording:
    """Tests for internal_recall_get_recording function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_recording

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_get_recording(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_gets_recording_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_get_recording

        mock_service = AsyncMock()
        mock_service.get_recording = AsyncMock(
            return_value={
                "success": True,
                "data": {"download_url": "https://recall.ai/recording/bot-123.mp4"},
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_get_recording(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_service.get_recording.assert_called_once_with("bot-123")


class TestInternalRecallRemoveBot:
    """Tests for internal_recall_remove_bot function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_service(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_remove_bot

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_recall_remove_bot(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_removes_bot_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_remove_bot

        mock_service = AsyncMock()
        mock_service.remove_bot = AsyncMock(
            return_value={
                "success": True,
                "message": "Bot removed successfully",
            }
        )

        with patch(
            "src.services.agents.internal_tools.recall_tools._get_recall_service",
            new_callable=AsyncMock,
            return_value=mock_service,
        ):
            result = await internal_recall_remove_bot(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_service.remove_bot.assert_called_once_with("bot-123")


class TestInternalRecallSummarizeMeeting:
    """Tests for internal_recall_summarize_meeting function."""

    @pytest.mark.asyncio
    async def test_returns_error_if_transcript_fails(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_summarize_meeting

        with patch(
            "src.services.agents.internal_tools.recall_tools.internal_recall_get_transcript",
            new_callable=AsyncMock,
            return_value={"success": False, "error": "Transcript not available"},
        ):
            result = await internal_recall_summarize_meeting(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_returns_error_if_no_transcript_content(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_summarize_meeting

        with patch(
            "src.services.agents.internal_tools.recall_tools.internal_recall_get_transcript",
            new_callable=AsyncMock,
            return_value={"success": True, "data": {"full_text": ""}},
        ):
            result = await internal_recall_summarize_meeting(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "No transcript content" in result["error"]

    @pytest.mark.asyncio
    async def test_summarizes_meeting_successfully(self):
        from src.services.agents.internal_tools.recall_tools import internal_recall_summarize_meeting

        with (
            patch(
                "src.services.agents.internal_tools.recall_tools.internal_recall_get_transcript",
                new_callable=AsyncMock,
                return_value={
                    "success": True,
                    "data": {
                        "full_text": "Meeting discussion about project updates.",
                        "segment_count": 5,
                        "segments": [],
                    },
                },
            ),
            patch(
                "src.services.agents.internal_tools.recall_tools.internal_recall_get_bot_status",
                new_callable=AsyncMock,
                return_value={
                    "success": True,
                    "data": {
                        "meeting_url": "https://zoom.us/j/123",
                        "bot_name": "Test Bot",
                        "created_at": "2025-01-10T10:00:00Z",
                    },
                },
            ),
        ):
            result = await internal_recall_summarize_meeting(
                bot_id="bot-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert "transcript" in result["data"]
            assert "meeting_info" in result["data"]
