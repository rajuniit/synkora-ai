"""
Tests for zoom_tools.py - Zoom Meeting Management Tools

Tests the Zoom tools for creating, listing, updating, deleting meetings,
and accessing recordings.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalZoomCreateMeeting:
    """Tests for internal_zoom_create_meeting function."""

    @pytest.mark.asyncio
    async def test_requires_topic(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        result = await internal_zoom_create_meeting(topic="", start_time="2025-01-10T10:00:00Z", duration=60)

        assert result["success"] is False
        assert "topic is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_start_time(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        result = await internal_zoom_create_meeting(topic="Test Meeting", start_time="", duration=60)

        assert result["success"] is False
        assert "Start time" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_positive_duration(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        result = await internal_zoom_create_meeting(
            topic="Test Meeting", start_time="2025-01-10T10:00:00Z", duration=-10
        )

        assert result["success"] is False
        assert "positive integer" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        result = await internal_zoom_create_meeting(
            topic="Test Meeting",
            start_time="2025-01-10T10:00:00Z",
            duration=60,
            runtime_context=None,
        )

        assert result["success"] is False
        assert "No runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_without_token(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value=None)

        # Patch at source module since import is inside function
        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            result = await internal_zoom_create_meeting(
                topic="Test Meeting",
                start_time="2025-01-10T10:00:00Z",
                duration=60,
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "authentication expired" in result["error"]

    @pytest.mark.asyncio
    async def test_creates_meeting_successfully(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_create_meeting

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(
            return_value={
                "id": 12345678,
                "topic": "Team Standup",
                "start_time": "2025-01-10T10:00:00Z",
                "duration": 30,
                "timezone": "America/New_York",
                "join_url": "https://zoom.us/j/12345678",
                "password": "abc123",
                "host_email": "host@example.com",
                "agenda": "Daily standup",
            }
        )

        mock_session = MagicMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=False)

        # Patch at source module since import is inside function
        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch(
                "src.services.agents.internal_tools.zoom_tools._get_zoom_user_timezone",
                new_callable=AsyncMock,
                return_value="America/New_York",
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_zoom_create_meeting(
                topic="Team Standup",
                start_time="2025-01-10T10:00:00Z",
                duration=30,
                agenda="Daily standup",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["data"]["meeting_id"] == 12345678
            assert result["data"]["join_url"] == "https://zoom.us/j/12345678"


class TestInternalZoomListMeetings:
    """Tests for internal_zoom_list_meetings function."""

    @pytest.mark.asyncio
    async def test_validates_meeting_type(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_list_meetings

        result = await internal_zoom_list_meetings(meeting_type="invalid_type")

        assert result["success"] is False
        assert "Invalid meeting_type" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_list_meetings

        result = await internal_zoom_list_meetings(runtime_context=None)

        assert result["success"] is False
        assert "No runtime context" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_meetings_successfully(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_list_meetings

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "meetings": [
                    {
                        "id": 111,
                        "topic": "Meeting 1",
                        "start_time": "2025-01-10T10:00:00Z",
                        "duration": 30,
                        "timezone": "UTC",
                        "join_url": "https://zoom.us/j/111",
                        "agenda": "",
                    },
                    {
                        "id": 222,
                        "topic": "Meeting 2",
                        "start_time": "2025-01-11T14:00:00Z",
                        "duration": 60,
                        "timezone": "UTC",
                        "join_url": "https://zoom.us/j/222",
                        "agenda": "Quarterly review",
                    },
                ]
            }
        )

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_zoom_list_meetings(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["data"]["total_count"] == 2
            assert len(result["data"]["meetings"]) == 2


class TestInternalZoomGetMeeting:
    """Tests for internal_zoom_get_meeting function."""

    @pytest.mark.asyncio
    async def test_requires_meeting_id(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_get_meeting

        result = await internal_zoom_get_meeting(meeting_id="")

        assert result["success"] is False
        assert "Meeting ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_get_meeting

        result = await internal_zoom_get_meeting(meeting_id="12345", runtime_context=None)

        assert result["success"] is False
        assert "No runtime context" in result["error"]


class TestInternalZoomUpdateMeeting:
    """Tests for internal_zoom_update_meeting function."""

    @pytest.mark.asyncio
    async def test_requires_meeting_id(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_update_meeting

        result = await internal_zoom_update_meeting(meeting_id="")

        assert result["success"] is False
        assert "Meeting ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_update_fields(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_update_meeting

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            result = await internal_zoom_update_meeting(
                meeting_id="12345",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False
            assert "No update fields" in result["error"]

    @pytest.mark.asyncio
    async def test_updates_meeting_successfully(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_update_meeting

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        mock_response = AsyncMock()
        mock_response.status = 204

        mock_session = MagicMock()
        mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_zoom_update_meeting(
                meeting_id="12345",
                topic="Updated Topic",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert "topic" in result["updated_fields"]


class TestInternalZoomDeleteMeeting:
    """Tests for internal_zoom_delete_meeting function."""

    @pytest.mark.asyncio
    async def test_requires_meeting_id(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_delete_meeting

        result = await internal_zoom_delete_meeting(meeting_id="")

        assert result["success"] is False
        assert "Meeting ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_deletes_meeting_successfully(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_delete_meeting

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        mock_response = AsyncMock()
        mock_response.status = 204

        mock_session = MagicMock()
        mock_session.delete.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.delete.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_zoom_delete_meeting(
                meeting_id="12345",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True


class TestInternalZoomGetMeetingRecordings:
    """Tests for internal_zoom_get_meeting_recordings function."""

    @pytest.mark.asyncio
    async def test_requires_meeting_id(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_get_meeting_recordings

        result = await internal_zoom_get_meeting_recordings(meeting_id="")

        assert result["success"] is False
        assert "Meeting ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_recordings_successfully(self):
        from src.services.agents.internal_tools.zoom_tools import internal_zoom_get_meeting_recordings

        mock_resolver = MagicMock()
        mock_resolver.get_zoom_token = AsyncMock(return_value="zoom-token-123")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "recording_files": [
                    {
                        "id": "rec-1",
                        "meeting_id": "12345",
                        "recording_start": "2025-01-10T10:00:00Z",
                        "recording_end": "2025-01-10T10:30:00Z",
                        "file_type": "MP4",
                        "file_size": 50000000,
                        "download_url": "https://zoom.us/download/rec-1",
                        "play_url": "https://zoom.us/play/rec-1",
                        "status": "completed",
                    }
                ]
            }
        )

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("aiohttp.ClientSession") as mock_client,
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await internal_zoom_get_meeting_recordings(
                meeting_id="12345",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["data"]["total_count"] == 1
            assert result["data"]["recordings"][0]["file_type"] == "MP4"
