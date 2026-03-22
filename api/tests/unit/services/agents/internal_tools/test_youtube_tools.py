"""
Tests for youtube_tools.py - YouTube Tools

Tests the YouTube transcript extraction functionality.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestExtractVideoId:
    """Tests for _extract_video_id helper function."""

    def test_extracts_from_standard_url(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"

    def test_extracts_from_short_url(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"

    def test_extracts_from_embed_url(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"

    def test_returns_direct_id(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"

    def test_handles_empty_input(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("")
        assert result == ""

    def test_extracts_from_url_with_params(self):
        from src.services.agents.internal_tools.youtube_tools import _extract_video_id

        result = _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120")
        assert result == "dQw4w9WgXcQ"


class TestInternalYoutubeGetTranscript:
    """Tests for internal_youtube_get_transcript function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_api_not_available(self):
        from src.services.agents.internal_tools import youtube_tools

        # Temporarily set API unavailable
        original_value = youtube_tools._TRANSCRIPT_API_AVAILABLE
        youtube_tools._TRANSCRIPT_API_AVAILABLE = False

        try:
            result = await youtube_tools.internal_youtube_get_transcript(video_id="dQw4w9WgXcQ")

            assert result["success"] is False
            assert "not installed" in result["error"]
        finally:
            youtube_tools._TRANSCRIPT_API_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_video_id(self):
        from src.services.agents.internal_tools import youtube_tools

        if not youtube_tools._TRANSCRIPT_API_AVAILABLE:
            pytest.skip("youtube-transcript-api not installed")

        result = await youtube_tools.internal_youtube_get_transcript(video_id="")

        assert result["success"] is False
        assert "Invalid video ID" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_transcript_successfully(self):
        from src.services.agents.internal_tools import youtube_tools

        if not youtube_tools._TRANSCRIPT_API_AVAILABLE:
            pytest.skip("youtube-transcript-api not installed")

        # Mock the transcript API
        mock_transcript = MagicMock()
        mock_transcript.is_generated = False
        mock_transcript.language_code = "en"
        mock_transcript.fetch.return_value = [
            {"text": "Hello", "start": 0.0, "duration": 1.5},
            {"text": "world", "start": 1.5, "duration": 1.0},
        ]

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript

        with patch(
            "src.services.agents.internal_tools.youtube_tools.YouTubeTranscriptApi.list_transcripts",
            return_value=mock_transcript_list,
        ):
            result = await youtube_tools.internal_youtube_get_transcript(
                video_id="dQw4w9WgXcQ",
                languages=["en"],
            )

            assert result["success"] is True
            assert result["video_id"] == "dQw4w9WgXcQ"
            assert result["language"] == "en"
            assert "Hello" in result["full_text"]
            assert result["segment_count"] == 2


class TestInternalYoutubeListTranscriptLanguages:
    """Tests for internal_youtube_list_transcript_languages function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_api_not_available(self):
        from src.services.agents.internal_tools import youtube_tools

        original_value = youtube_tools._TRANSCRIPT_API_AVAILABLE
        youtube_tools._TRANSCRIPT_API_AVAILABLE = False

        try:
            result = await youtube_tools.internal_youtube_list_transcript_languages(video_id="dQw4w9WgXcQ")

            assert result["success"] is False
            assert "not installed" in result["error"]
        finally:
            youtube_tools._TRANSCRIPT_API_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_video_id(self):
        from src.services.agents.internal_tools import youtube_tools

        if not youtube_tools._TRANSCRIPT_API_AVAILABLE:
            pytest.skip("youtube-transcript-api not installed")

        result = await youtube_tools.internal_youtube_list_transcript_languages(video_id="")

        assert result["success"] is False
        assert "Invalid video ID" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_languages_successfully(self):
        from src.services.agents.internal_tools import youtube_tools

        if not youtube_tools._TRANSCRIPT_API_AVAILABLE:
            pytest.skip("youtube-transcript-api not installed")

        mock_transcript_en = MagicMock()
        mock_transcript_en.language = "English"
        mock_transcript_en.language_code = "en"
        mock_transcript_en.is_generated = False
        mock_transcript_en.is_translatable = True

        mock_transcript_es = MagicMock()
        mock_transcript_es.language = "Spanish"
        mock_transcript_es.language_code = "es"
        mock_transcript_es.is_generated = True
        mock_transcript_es.is_translatable = True

        mock_transcript_list = MagicMock()
        mock_transcript_list.__iter__ = lambda self: iter([mock_transcript_en, mock_transcript_es])

        with patch(
            "src.services.agents.internal_tools.youtube_tools.YouTubeTranscriptApi.list_transcripts",
            return_value=mock_transcript_list,
        ):
            result = await youtube_tools.internal_youtube_list_transcript_languages(video_id="dQw4w9WgXcQ")

            assert result["success"] is True
            assert result["count"] == 2
            assert result["languages"][0]["language_code"] == "en"


class TestInternalYoutubeGetTranscriptSegment:
    """Tests for internal_youtube_get_transcript_segment function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_api_not_available(self):
        from src.services.agents.internal_tools import youtube_tools

        original_value = youtube_tools._TRANSCRIPT_API_AVAILABLE
        youtube_tools._TRANSCRIPT_API_AVAILABLE = False

        try:
            result = await youtube_tools.internal_youtube_get_transcript_segment(
                video_id="dQw4w9WgXcQ",
                start_time=0.0,
                end_time=30.0,
            )

            assert result["success"] is False
            assert "not installed" in result["error"]
        finally:
            youtube_tools._TRANSCRIPT_API_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_filters_segments_by_time_range(self):
        from src.services.agents.internal_tools import youtube_tools

        if not youtube_tools._TRANSCRIPT_API_AVAILABLE:
            pytest.skip("youtube-transcript-api not installed")

        mock_transcript = MagicMock()
        mock_transcript.is_generated = False
        mock_transcript.language_code = "en"
        mock_transcript.fetch.return_value = [
            {"text": "First", "start": 0.0, "duration": 10.0},
            {"text": "Second", "start": 10.0, "duration": 10.0},
            {"text": "Third", "start": 20.0, "duration": 10.0},
            {"text": "Fourth", "start": 30.0, "duration": 10.0},
        ]

        mock_transcript_list = MagicMock()
        mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript

        with patch(
            "src.services.agents.internal_tools.youtube_tools.YouTubeTranscriptApi.list_transcripts",
            return_value=mock_transcript_list,
        ):
            result = await youtube_tools.internal_youtube_get_transcript_segment(
                video_id="dQw4w9WgXcQ",
                start_time=5.0,
                end_time=25.0,
                languages=["en"],
            )

            assert result["success"] is True
            # Should include segments that start between 5 and 25 seconds
            assert result["segment_count"] >= 1
