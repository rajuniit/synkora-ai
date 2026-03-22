"""
YouTube Tools for video transcript extraction and summarization.
Uses youtube-transcript-api for transcript extraction (no auth required).

This tool enables:
- Transcript extraction from YouTube videos
- Multi-language support with translation
- Video summarization via transcript processing
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Check for youtube-transcript-api availability
_TRANSCRIPT_API_AVAILABLE = False
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    _TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    logger.warning("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")


def _extract_video_id(url_or_id: str) -> str:
    """
    Extract video ID from YouTube URL or return as-is if already an ID.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - VIDEO_ID (direct ID)
    """
    if not url_or_id:
        return ""

    # Already a video ID (11 characters, alphanumeric with _ and -)
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id

    # YouTube URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    return url_or_id


async def internal_youtube_get_transcript(
    video_id: str,
    languages: list[str] | None = None,
    translate_to: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get transcript/captions from a YouTube video.

    Args:
        video_id: YouTube video ID or URL
        languages: Preferred languages in order of preference (e.g., ['en', 'es'])
                  Defaults to ['en'] if not specified
        translate_to: Translate transcript to this language code (e.g., 'en', 'es', 'fr')

    Returns:
        Transcript text with metadata
    """
    if not _TRANSCRIPT_API_AVAILABLE:
        return {
            "success": False,
            "error": "youtube-transcript-api not installed. Install with: pip install youtube-transcript-api",
        }

    try:
        # Extract video ID from URL if needed
        video_id = _extract_video_id(video_id)
        if not video_id:
            return {"success": False, "error": "Invalid video ID or URL"}

        # Default to English
        if not languages:
            languages = ["en"]

        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to find transcript in preferred languages
        transcript = None
        transcript_language = None

        # First, try manually created transcripts
        for lang in languages:
            try:
                transcript = transcript_list.find_manually_created_transcript([lang])
                transcript_language = lang
                break
            except NoTranscriptFound:
                continue

        # If no manual transcript, try auto-generated
        if not transcript:
            for lang in languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    transcript_language = lang
                    break
                except NoTranscriptFound:
                    continue

        # If still no transcript, get any available
        if not transcript:
            try:
                # Get first available transcript
                for t in transcript_list:
                    transcript = t
                    transcript_language = t.language_code
                    break
            except Exception:
                pass

        if not transcript:
            return {
                "success": False,
                "error": "No transcript available for this video",
                "video_id": video_id,
            }

        # Translate if requested
        if translate_to and translate_to != transcript_language:
            try:
                transcript = transcript.translate(translate_to)
                transcript_language = translate_to
            except Exception as e:
                logger.warning(f"Translation failed: {e}")

        # Fetch the transcript data
        transcript_data = transcript.fetch()

        # Combine into full text
        full_text = " ".join([entry["text"] for entry in transcript_data])

        # Also create timestamped version
        timestamped_entries = []
        for entry in transcript_data:
            start_time = entry["start"]
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamped_entries.append(
                {
                    "timestamp": f"{minutes:02d}:{seconds:02d}",
                    "start_seconds": entry["start"],
                    "duration": entry["duration"],
                    "text": entry["text"],
                }
            )

        return {
            "success": True,
            "video_id": video_id,
            "language": transcript_language,
            "is_generated": transcript.is_generated,
            "full_text": full_text,
            "word_count": len(full_text.split()),
            "segments": timestamped_entries,
            "segment_count": len(timestamped_entries),
        }

    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Transcripts are disabled for this video",
            "video_id": video_id,
        }
    except VideoUnavailable:
        return {
            "success": False,
            "error": "Video is unavailable",
            "video_id": video_id,
        }
    except Exception as e:
        logger.error(f"Failed to get YouTube transcript: {e}")
        return {"success": False, "error": str(e), "video_id": video_id}


async def internal_youtube_list_transcript_languages(
    video_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    List available transcript languages for a YouTube video.

    Args:
        video_id: YouTube video ID or URL

    Returns:
        List of available languages with metadata
    """
    if not _TRANSCRIPT_API_AVAILABLE:
        return {
            "success": False,
            "error": "youtube-transcript-api not installed. Install with: pip install youtube-transcript-api",
        }

    try:
        video_id = _extract_video_id(video_id)
        if not video_id:
            return {"success": False, "error": "Invalid video ID or URL"}

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        languages = []
        for transcript in transcript_list:
            languages.append(
                {
                    "language": transcript.language,
                    "language_code": transcript.language_code,
                    "is_generated": transcript.is_generated,
                    "is_translatable": transcript.is_translatable,
                }
            )

        return {
            "success": True,
            "video_id": video_id,
            "languages": languages,
            "count": len(languages),
        }

    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Transcripts are disabled for this video",
            "video_id": video_id,
        }
    except VideoUnavailable:
        return {
            "success": False,
            "error": "Video is unavailable",
            "video_id": video_id,
        }
    except Exception as e:
        logger.error(f"Failed to list transcript languages: {e}")
        return {"success": False, "error": str(e), "video_id": video_id}


async def internal_youtube_get_transcript_segment(
    video_id: str,
    start_time: float,
    end_time: float,
    languages: list[str] | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get a specific segment of transcript by time range.

    Args:
        video_id: YouTube video ID or URL
        start_time: Start time in seconds
        end_time: End time in seconds
        languages: Preferred languages

    Returns:
        Transcript segment for the specified time range
    """
    if not _TRANSCRIPT_API_AVAILABLE:
        return {
            "success": False,
            "error": "youtube-transcript-api not installed",
        }

    try:
        # Get full transcript first
        result = await internal_youtube_get_transcript(
            video_id=video_id,
            languages=languages,
            config=config,
            runtime_context=runtime_context,
        )

        if not result.get("success"):
            return result

        # Filter segments by time range
        segments = result.get("segments", [])
        filtered_segments = [
            seg for seg in segments if seg["start_seconds"] >= start_time and seg["start_seconds"] <= end_time
        ]

        # Combine text
        segment_text = " ".join([seg["text"] for seg in filtered_segments])

        return {
            "success": True,
            "video_id": _extract_video_id(video_id),
            "start_time": start_time,
            "end_time": end_time,
            "text": segment_text,
            "segments": filtered_segments,
            "segment_count": len(filtered_segments),
        }

    except Exception as e:
        logger.error(f"Failed to get transcript segment: {e}")
        return {"success": False, "error": str(e)}
