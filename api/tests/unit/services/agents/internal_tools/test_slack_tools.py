"""
Tests for slack_tools.py - Slack Tools for Autonomous Agent Interaction

Tests the Slack tools that allow agents to interact with Slack channels,
including reading messages, sending messages, and searching.
"""

from unittest.mock import AsyncMock, patch

import pytest
from slack_sdk.errors import SlackApiError


class TestGetSlackClient:
    """Tests for _get_slack_client helper function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_agent_id(self):
        from src.services.agents.internal_tools.slack_tools import _get_slack_client

        result = await _get_slack_client({})
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_with_empty_runtime_context(self):
        from src.services.agents.internal_tools.slack_tools import _get_slack_client

        result = await _get_slack_client(None)
        assert result is None


class TestInternalSlackListChannels:
    """Tests for internal_slack_list_channels function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_slack_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_list_channels

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.return_value = None

            result = await internal_slack_list_channels(runtime_context={})

            assert result["success"] is False
            assert "No Slack connection" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_channels_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_list_channels

        mock_slack_client = AsyncMock()
        mock_slack_client.conversations_list.return_value = {
            "channels": [
                {
                    "id": "C123",
                    "name": "general",
                    "is_private": False,
                    "is_member": True,
                    "num_members": 50,
                    "topic": {"value": "General chat"},
                    "purpose": {"value": "Company announcements"},
                },
                {
                    "id": "C456",
                    "name": "random",
                    "is_private": False,
                    "is_member": True,
                    "num_members": 45,
                    "topic": {"value": ""},
                    "purpose": {"value": ""},
                },
            ],
            "response_metadata": {"next_cursor": ""},
        }

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_list_channels(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["channels"]) == 2
            assert result["channels"][0]["name"] == "general"

    @pytest.mark.asyncio
    async def test_handles_slack_api_error(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_list_channels

        mock_slack_client = AsyncMock()
        mock_slack_client.conversations_list.side_effect = SlackApiError(
            message="rate_limited", response={"error": "rate_limited"}
        )

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_list_channels(runtime_context={"agent_id": "test"})

            assert result["success"] is False


class TestInternalSlackReadChannelMessages:
    """Tests for internal_slack_read_channel_messages function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_slack_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_read_channel_messages

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_read_channel_messages(channel_id="C123", runtime_context={})

            assert result["success"] is False


class TestInternalSlackSendMessage:
    """Tests for internal_slack_send_message function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_slack_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_message

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_send_message(channel_id="C123", text="Hello!", runtime_context={})

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_sends_message_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_message

        mock_slack_client = AsyncMock()
        mock_slack_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C123",
        }

        with (
            patch(
                "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
            ) as mock_get,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Hello!"),
        ):
            mock_get.return_value = mock_slack_client

            result = await internal_slack_send_message(
                channel_id="C123", text="Hello!", runtime_context={"agent_id": "test"}
            )

            assert result["success"] is True
            assert result["message_ts"] == "1234567890.123456"

    @pytest.mark.asyncio
    async def test_sends_thread_reply(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_message

        mock_slack_client = AsyncMock()
        mock_slack_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.999999",
            "channel": "C123",
        }

        with (
            patch(
                "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
            ) as mock_get,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Thread reply!"),
        ):
            mock_get.return_value = mock_slack_client

            result = await internal_slack_send_message(
                channel_id="C123",
                text="Thread reply!",
                thread_ts="1234567890.123456",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            mock_slack_client.chat_postMessage.assert_called_once()
            call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
            assert call_kwargs["thread_ts"] == "1234567890.123456"


class TestInternalSlackJoinChannel:
    """Tests for internal_slack_join_channel function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_join_channel

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_join_channel(channel_id="C123", runtime_context={})

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_joins_channel_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_join_channel

        mock_slack_client = AsyncMock()
        mock_slack_client.conversations_join.return_value = {
            "ok": True,
            "channel": {"id": "C123", "name": "test-channel"},
        }

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_join_channel(channel_id="C123", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["channel_name"] == "test-channel"


class TestInternalSlackSearchMessages:
    """Tests for internal_slack_search_messages function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_search_messages

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_search_messages(query="keyword", runtime_context={})

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_searches_messages_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_search_messages

        mock_slack_client = AsyncMock()
        mock_slack_client.search_messages.return_value = {
            "ok": True,
            "messages": {
                "matches": [
                    {
                        "type": "message",
                        "text": "Test message with keyword",
                        "username": "testuser",
                        "ts": "1234567890.123456",
                        "channel": {"id": "C123", "name": "general"},
                        "permalink": "https://slack.com/archives/C123/p1234567890123456",
                    },
                ],
                "total": 1,
            },
        }

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_search_messages(query="keyword", runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["total_results"] == 1
            assert len(result["matches"]) == 1


class TestInternalSlackAddReaction:
    """Tests for internal_slack_add_reaction function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_add_reaction

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_add_reaction(
                channel_id="C123", timestamp="1234567890.123456", emoji="thumbsup", runtime_context={}
            )

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_adds_reaction_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_add_reaction

        mock_slack_client = AsyncMock()
        mock_slack_client.reactions_add.return_value = {"ok": True}

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_add_reaction(
                channel_id="C123", timestamp="1234567890.123456", emoji="thumbsup", runtime_context={"agent_id": "test"}
            )

            assert result["success"] is True
            assert result["emoji"] == "thumbsup"
            mock_slack_client.reactions_add.assert_called_once_with(
                channel="C123",
                timestamp="1234567890.123456",
                name="thumbsup",
            )

    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_add_reaction

        mock_slack_client = AsyncMock()
        mock_slack_client.reactions_add.side_effect = SlackApiError(
            message="invalid_name", response={"error": "invalid_name"}
        )

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_slack_client

            result = await internal_slack_add_reaction(
                channel_id="C123",
                timestamp="1234567890.123456",
                emoji="invalid_emoji",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is False


class TestInternalSlackSendDM:
    """Tests for internal_slack_send_dm function."""

    @pytest.mark.asyncio
    async def test_returns_error_without_client(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_dm

        with patch(
            "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await internal_slack_send_dm(user_id="U456", text="Hello!", runtime_context={})

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_sends_dm_successfully(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_dm

        mock_slack_client = AsyncMock()
        mock_slack_client.conversations_open.return_value = {
            "ok": True,
            "channel": {"id": "D123"},
        }
        mock_slack_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "D123",
        }

        with (
            patch(
                "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
            ) as mock_get,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Hello in DM!"),
        ):
            mock_get.return_value = mock_slack_client

            result = await internal_slack_send_dm(
                user_id="U456", text="Hello in DM!", runtime_context={"agent_id": "test"}
            )

            assert result["success"] is True
            assert result["user_id"] == "U456"
            mock_slack_client.conversations_open.assert_called_once_with(users=["U456"])

    @pytest.mark.asyncio
    async def test_handles_dm_channel_open_failure(self):
        from src.services.agents.internal_tools.slack_tools import internal_slack_send_dm

        mock_slack_client = AsyncMock()
        mock_slack_client.conversations_open.return_value = {
            "ok": True,
            "channel": {},  # Missing id
        }

        with (
            patch(
                "src.services.agents.internal_tools.slack_tools._get_slack_client", new_callable=AsyncMock
            ) as mock_get,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Hello!"),
        ):
            mock_get.return_value = mock_slack_client

            result = await internal_slack_send_dm(user_id="U456", text="Hello!", runtime_context={"agent_id": "test"})

            assert result["success"] is False
            assert "Could not open DM channel" in result["error"]
