"""
Tests for google_calendar_tools.py - Google Calendar Tools

Tests the Google Calendar integration for listing, creating, updating,
deleting events, and checking free/busy status.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalGoogleCalendarListEvents:
    """Tests for internal_google_calendar_list_events function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_list_events

        result = await internal_google_calendar_list_events(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_without_token(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_list_events

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value=None)

        with patch(
            "src.services.agents.credential_resolver.CredentialResolver",
            return_value=mock_resolver,
        ):
            result = await internal_google_calendar_list_events(runtime_context={"agent_id": "test"})

            assert result["success"] is False
            assert "authentication expired" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_events_successfully(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_list_events

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "event-1",
                    "summary": "Team Meeting",
                    "start": {"dateTime": "2025-01-10T10:00:00Z"},
                    "end": {"dateTime": "2025-01-10T11:00:00Z"},
                    "location": "Room 101",
                    "description": "Weekly sync",
                    "attendees": [{"email": "user@example.com"}],
                    "htmlLink": "https://calendar.google.com/event/1",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await internal_google_calendar_list_events(
                max_results=10,
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["count"] == 1
            assert result["events"][0]["summary"] == "Team Meeting"


class TestInternalGoogleCalendarGetEvent:
    """Tests for internal_google_calendar_get_event function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_get_event

        result = await internal_google_calendar_get_event(event_id="event-123", runtime_context=None)

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]


class TestInternalGoogleCalendarCreateEvent:
    """Tests for internal_google_calendar_create_event function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_create_event

        result = await internal_google_calendar_create_event(
            summary="Test Event",
            start_time="2025-01-10T10:00:00Z",
            end_time="2025-01-10T11:00:00Z",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]

    @pytest.mark.asyncio
    async def test_creates_event_successfully(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_create_event

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "event-123",
            "htmlLink": "https://calendar.google.com/event/123",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await internal_google_calendar_create_event(
                summary="Team Meeting",
                start_time="2025-01-10T10:00:00Z",
                end_time="2025-01-10T11:00:00Z",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["event_id"] == "event-123"


class TestInternalGoogleCalendarUpdateEvent:
    """Tests for internal_google_calendar_update_event function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_update_event

        result = await internal_google_calendar_update_event(
            event_id="event-123",
            summary="Updated Event",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]


class TestInternalGoogleCalendarDeleteEvent:
    """Tests for internal_google_calendar_delete_event function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_delete_event

        result = await internal_google_calendar_delete_event(
            event_id="event-123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]

    @pytest.mark.asyncio
    async def test_deletes_event_successfully(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_delete_event

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await internal_google_calendar_delete_event(
                event_id="event-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert "deleted" in result["message"].lower()


class TestInternalGoogleCalendarGetFreeBusy:
    """Tests for internal_google_calendar_get_free_busy function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_get_free_busy

        result = await internal_google_calendar_get_free_busy(
            time_min="2025-01-10T00:00:00Z",
            time_max="2025-01-10T23:59:59Z",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_free_busy_info(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_get_free_busy

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "calendars": {"primary": {"busy": [{"start": "2025-01-10T10:00:00Z", "end": "2025-01-10T11:00:00Z"}]}}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await internal_google_calendar_get_free_busy(
                time_min="2025-01-10T00:00:00Z",
                time_max="2025-01-10T23:59:59Z",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert "primary" in result["free_busy"]


class TestInternalGoogleCalendarListCalendars:
    """Tests for internal_google_calendar_list_calendars function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_list_calendars

        result = await internal_google_calendar_list_calendars(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context not available" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_calendars_successfully(self):
        from src.services.agents.internal_tools.google_calendar_tools import internal_google_calendar_list_calendars

        mock_resolver = MagicMock()
        mock_resolver.get_google_calendar_token = AsyncMock(return_value="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "primary",
                    "summary": "Work Calendar",
                    "description": "Main calendar",
                    "primary": True,
                    "accessRole": "owner",
                },
                {
                    "id": "cal-2",
                    "summary": "Personal",
                    "primary": False,
                    "accessRole": "reader",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.services.agents.credential_resolver.CredentialResolver",
                return_value=mock_resolver,
            ),
            patch("httpx.AsyncClient", return_value=mock_client),
        ):
            result = await internal_google_calendar_list_calendars(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert len(result["calendars"]) == 2
            assert result["calendars"][0]["id"] == "primary"
            assert result["calendars"][0]["primary"] is True
