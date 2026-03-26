import asyncio
from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.slack_bot import SlackBot, SlackConversation
from src.services.slack.slack_socket_service import SlackSocketService


class TestSlackSocketService:
    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        session.get = AsyncMock()
        # Setup execute to return proper result mock (sync scalars().all())
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = []
        mock_execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_execute_result)
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        # Reset class-level handlers for isolation
        SlackSocketService._active_handlers = {}
        return SlackSocketService(mock_db_session)

    @pytest.fixture
    def mock_slack_bot(self):
        bot = MagicMock(spec=SlackBot)
        bot.id = uuid4()
        bot.agent_id = uuid4()
        bot.bot_name = "TestBot"
        bot.slack_app_id = "APP123"
        bot.slack_bot_token = "encrypted_bot_token"
        bot.slack_app_token = "encrypted_app_token"
        bot.slack_workspace_id = None
        bot.slack_workspace_name = None
        bot.connection_status = "disconnected"
        return bot

    @pytest.mark.asyncio
    async def test_start_bot_success(self, service, mock_slack_bot, mock_db_session):
        with (
            patch("src.services.slack.slack_socket_service.decrypt_value", side_effect=lambda x: f"dec_{x}"),
            patch("src.services.slack.slack_socket_service.AsyncApp") as MockApp,
            patch("src.services.slack.slack_socket_service.AsyncWebClient") as MockClient,
            patch("src.services.slack.slack_socket_service.AsyncSocketModeHandler") as MockHandler,
        ):
            # Setup mocks
            mock_client_instance = MockClient.return_value
            mock_client_instance.auth_test = AsyncMock(return_value={"team_id": "T1", "team": "Team"})

            mock_handler_instance = MockHandler.return_value
            mock_handler_instance.start_async = AsyncMock()

            # Call method
            result = await service.start_bot(mock_slack_bot)

            assert result is True
            assert str(mock_slack_bot.id) in service.active_handlers
            assert mock_slack_bot.connection_status == "connected"
            assert mock_slack_bot.slack_workspace_id == "T1"

            MockApp.assert_called_once_with(token="dec_encrypted_bot_token")
            MockHandler.assert_called_once()
            # Verify handler started in background - trickier with create_task but valid here

            mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_start_bot_error(self, service, mock_slack_bot, mock_db_session):
        with patch("src.services.slack.slack_socket_service.decrypt_value", side_effect=Exception("Decrypt Error")):
            result = await service.start_bot(mock_slack_bot)

            assert result is False
            assert mock_slack_bot.connection_status == "error"
            mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_stop_bot(self, service, mock_db_session):
        bot_id = uuid4()
        mock_handler = MagicMock()
        mock_handler.close_async = AsyncMock()
        service.active_handlers[str(bot_id)] = mock_handler

        mock_slack_bot = MagicMock(spec=SlackBot)
        mock_db_session.get.return_value = mock_slack_bot

        result = await service.stop_bot(bot_id)

        assert result is True
        assert str(bot_id) not in service.active_handlers
        mock_handler.close_async.assert_called_once()
        assert mock_slack_bot.connection_status == "disconnected"
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_stop_bot_not_running(self, service, mock_db_session):
        bot_id = uuid4()
        mock_slack_bot = MagicMock(spec=SlackBot)
        mock_db_session.get.return_value = mock_slack_bot

        result = await service.stop_bot(bot_id)

        assert result is True
        assert mock_slack_bot.connection_status == "disconnected"

    def test_register_event_handlers(self, service, mock_slack_bot):
        mock_app = MagicMock()
        service._register_event_handlers(mock_app, mock_slack_bot)

        assert mock_app.event.call_count >= 2
        calls = [call("app_mention"), call("message")]
        mock_app.event.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_handle_message_success(self, service, mock_slack_bot, mock_db_session):
        # Mock dependencies
        mock_client = MagicMock()
        mock_client.users_info = AsyncMock(return_value={"user": {"real_name": "User Name", "name": "username"}})
        mock_client.conversations_info = AsyncMock(return_value={"channel": {"name": "general"}})
        mock_client.auth_test = AsyncMock(return_value={"url": "https://workspace.slack.com/"})
        mock_client.chat_postMessage = AsyncMock()
        mock_client.chat_update = AsyncMock()

        mock_say = AsyncMock()

        mock_conversation = MagicMock(spec=Conversation, id=uuid4(), message_count=0)

        # Patching inside the method imports and other internal calls
        with (
            patch.object(service, "_get_or_create_conversation", return_value=mock_conversation) as mock_get_conv,
            patch.object(service, "_remove_bot_mention", return_value="hello"),
            patch.object(service, "_extract_user_mentions", return_value=[]),
            patch("src.services.agents.chat_stream_service.ChatStreamService") as MockChatStream,
            patch(
                "src.services.slack.formatters.create_slack_blocks", return_value=[{"type": "section"}]
            ) as mock_create_blocks,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Response"),
            patch("src.services.slack.slack_socket_service.SlackStatusService") as MockStatusService,
            patch("src.services.conversation_service.ConversationService") as MockConvService,
        ):
            # Mock status service
            mock_status_instance = AsyncMock()
            mock_status_instance.set_thinking = AsyncMock(return_value=True)
            mock_status_instance.clear_thinking = AsyncMock(return_value=True)
            MockStatusService.return_value = mock_status_instance

            # Mock ConversationService
            MockConvService.get_conversation_history_cached = AsyncMock(return_value=[])

            # Setup agent
            mock_agent = MagicMock(spec=Agent)
            mock_agent.agent_name = "Agent Name"
            mock_db_session.get.return_value = mock_agent

            # Setup stream response mock (async generator)
            async def async_gen(*args, **kwargs):
                yield 'data: {"type": "chunk", "content": "Resp"}'
                yield 'data: {"type": "chunk", "content": "onse"}'

            mock_chat_stream_instance = MockChatStream.return_value
            mock_chat_stream_instance.stream_agent_response = async_gen

            # Call method
            await service._handle_message(
                slack_bot=mock_slack_bot,
                channel_id="C1",
                user_id="U1",
                text="<@BOT> hello",
                message_ts="123456.789",
                thread_ts="ts1",
                say=mock_say,
                client=mock_client,
            )

            # Verify flow
            mock_get_conv.assert_called_once()
            mock_client.users_info.assert_called_once_with(user="U1")

            # Verify DB additions (user message + assistant message)
            assert mock_db_session.add.call_count >= 2

            mock_create_blocks.assert_called_with("Response")

            mock_say.assert_called_once_with(text="Response", blocks=[{"type": "section"}], thread_ts="ts1")

    @pytest.mark.asyncio
    async def test_handle_message_chunked(self, service, mock_slack_bot, mock_db_session):
        # Mock dependencies
        mock_client = MagicMock()
        mock_client.users_info = AsyncMock(return_value={"user": {"real_name": "User Name", "name": "username"}})
        mock_client.conversations_info = AsyncMock(return_value={"channel": {"name": "general"}})
        mock_client.auth_test = AsyncMock(return_value={"url": "https://workspace.slack.com/"})
        mock_client.chat_postMessage = AsyncMock()
        mock_say = AsyncMock()
        mock_conversation = MagicMock(spec=Conversation, id=uuid4(), message_count=0)

        with (
            patch.object(service, "_get_or_create_conversation", return_value=mock_conversation),
            patch.object(service, "_remove_bot_mention", return_value="hello"),
            patch.object(service, "_extract_user_mentions", return_value=[]),
            patch("src.services.agents.chat_stream_service.ChatStreamService") as MockChatStream,
            patch("src.services.slack.formatters.create_slack_blocks") as mock_create_blocks,
            patch("src.services.slack.formatters.chunk_blocks") as mock_chunk_blocks,
            patch("src.services.slack.formatters.format_text_for_slack", return_value="Response"),
            patch("src.services.slack.slack_socket_service.SlackStatusService") as MockStatusService,
            patch("src.services.conversation_service.ConversationService") as MockConvService,
        ):
            # Mock status service
            mock_status_instance = AsyncMock()
            mock_status_instance.set_thinking = AsyncMock(return_value=True)
            mock_status_instance.clear_thinking = AsyncMock(return_value=True)
            MockStatusService.return_value = mock_status_instance

            # Mock ConversationService
            MockConvService.get_conversation_history_cached = AsyncMock(return_value=[])

            mock_agent = MagicMock(spec=Agent)
            mock_agent.agent_name = "Agent"
            mock_db_session.get.return_value = mock_agent

            async def async_gen(*args, **kwargs):
                yield 'data: {"type": "chunk", "content": "Long Response"}'

            mock_chat_stream_instance = MockChatStream.return_value
            mock_chat_stream_instance.stream_agent_response = async_gen

            # Return many blocks to trigger chunking
            blocks = [{"type": "section"}] * 55
            mock_create_blocks.return_value = blocks

            # Chunking logic
            chunk1 = blocks[:50]
            chunk2 = blocks[50:]
            mock_chunk_blocks.return_value = [chunk1, chunk2]

            await service._handle_message(
                slack_bot=mock_slack_bot,
                channel_id="C1",
                user_id="U1",
                text="hello",
                message_ts="123456.789",
                thread_ts=None,
                say=mock_say,
                client=mock_client,
            )

            mock_chunk_blocks.assert_called_once_with(blocks)
            assert mock_say.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_message_error(self, service, mock_slack_bot, mock_db_session):
        mock_say = AsyncMock()

        # Force error in _get_or_create_conversation
        with patch.object(service, "_get_or_create_conversation", side_effect=Exception("Error")):
            await service._handle_message(
                slack_bot=mock_slack_bot,
                channel_id="C1",
                user_id="U1",
                text="hello",
                message_ts="123456.789",
                thread_ts=None,
                say=mock_say,
                client=MagicMock(),
            )

            mock_db_session.rollback.assert_called_once()
            mock_say.assert_called_once()
            assert "error" in mock_say.call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_existing(self, service, mock_slack_bot, mock_db_session):
        # Mock DB execute result
        mock_result = MagicMock()
        mock_slack_conv = MagicMock(spec=SlackConversation, conversation_id=uuid4())
        mock_result.scalar_one_or_none.return_value = mock_slack_conv
        mock_db_session.execute.return_value = mock_result

        mock_conversation = MagicMock(spec=Conversation)
        mock_db_session.get.return_value = mock_conversation

        result = await service._get_or_create_conversation(mock_slack_bot, "C1", "U1", None)

        assert result == mock_conversation
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_new(self, service, mock_slack_bot, mock_db_session):
        # Mock DB execute result — implementation uses scalars().first(), not scalar_one_or_none()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await service._get_or_create_conversation(mock_slack_bot, "C1", "U1", "ts1")

        assert isinstance(result, Conversation)
        assert mock_db_session.add.call_count == 2  # Conversation + SlackConversation
        mock_db_session.commit.assert_called()

    def test_remove_bot_mention(self, service):
        text = "<@APP123> hello world"
        result = service._remove_bot_mention(text, "APP123")
        assert result == "hello world"

        text = "hello <@APP123>"
        result = service._remove_bot_mention(text, "APP123")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_get_bot_status(self, service, mock_db_session, mock_slack_bot):
        bot_id = uuid4()
        mock_slack_bot.last_connected_at = datetime.now(UTC)
        mock_db_session.get.return_value = mock_slack_bot

        # Mock active handler
        service.active_handlers[str(bot_id)] = MagicMock()

        status = await service.get_bot_status(bot_id)

        assert status["bot_id"] == str(bot_id)
        assert status["is_running"] is True
        assert status["connection_status"] == "disconnected"  # mock default
        assert status["last_connected_at"] is not None
