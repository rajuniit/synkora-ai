"""Tests for ModelService."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.core.errors import NotFoundError, ValidationError
from src.core.model_providers import ModelConfig, ModelResponse
from src.models import App, MessageRole, MessageStatus
from src.services.model_service import ModelService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def model_service(mock_db):
    """Create ModelService instance."""
    with patch("src.services.model_service.ConversationService"):
        service = ModelService(mock_db)
        service.conversation_service = AsyncMock()
        return service


@pytest.fixture
def sample_app():
    """Create sample app using Mock to avoid required fields."""
    app = Mock(spec=App)
    app.id = uuid4()
    app.name = "Test App"
    app.model_config = {
        "provider": "openai",
        "api_key": "test-key",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    return app


@pytest.fixture
def sample_conversation():
    """Create sample conversation with messages."""
    conversation = Mock()
    conversation.id = uuid4()
    conversation.app_id = uuid4()
    conversation.messages = [
        Mock(
            id=uuid4(),
            role=MessageRole.USER,
            content="Hello",
            is_completed=Mock(return_value=True),
        ),
        Mock(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Hi there!",
            is_completed=Mock(return_value=True),
        ),
    ]
    return conversation


class TestGetProviderFromApp:
    """Tests for _get_provider_from_app method."""

    def test_get_provider_success(self, model_service, sample_app):
        """Test successfully getting provider from app."""
        with patch("src.services.model_service.ModelProviderFactory.create_from_config") as mock_factory:
            mock_provider = Mock()
            mock_factory.return_value = mock_provider

            result = model_service._get_provider_from_app(sample_app)

            assert result == mock_provider
            mock_factory.assert_called_once_with(sample_app.model_config)

    def test_get_provider_missing_provider(self, model_service):
        """Test error when provider is missing."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = {"api_key": "test-key"}

        with pytest.raises(ValidationError, match="Model provider not configured"):
            model_service._get_provider_from_app(app)

    def test_get_provider_missing_api_key(self, model_service):
        """Test error when API key is missing."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = {"provider": "openai"}

        with pytest.raises(ValidationError, match="API key not configured"):
            model_service._get_provider_from_app(app)

    def test_get_provider_no_model_config(self, model_service):
        """Test error when model_config is None."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = None

        with pytest.raises(ValidationError, match="Model provider not configured"):
            model_service._get_provider_from_app(app)


class TestGetModelConfigFromApp:
    """Tests for _get_model_config_from_app method."""

    def test_get_config_success(self, model_service, sample_app):
        """Test successfully getting model config."""
        result = model_service._get_model_config_from_app(sample_app)

        assert isinstance(result, ModelConfig)
        assert result.model == "gpt-4"
        assert result.temperature == 0.7
        assert result.max_tokens == 1000

    def test_get_config_with_defaults(self, model_service):
        """Test getting config with default values."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = {"provider": "openai", "api_key": "test", "model": "gpt-3.5-turbo"}

        result = model_service._get_model_config_from_app(app)

        assert result.model == "gpt-3.5-turbo"
        assert result.temperature == 0.7  # default
        assert result.max_tokens == 1000  # default
        assert result.stream is False  # default

    def test_get_config_missing_model(self, model_service):
        """Test error when model is missing."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = {"provider": "openai", "api_key": "test"}

        with pytest.raises(ValidationError, match="Model not specified"):
            model_service._get_model_config_from_app(app)

    def test_get_config_no_model_config(self, model_service):
        """Test error when model_config is None."""
        app = Mock(spec=App)
        app.id = uuid4()
        app.name = "Test App"
        app.model_config = None

        with pytest.raises(ValidationError, match="Model not specified"):
            model_service._get_model_config_from_app(app)


class TestGenerateResponse:
    """Tests for generate_response method."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self, model_service, sample_app, sample_conversation, mock_db):
        """Test successfully generating a response."""
        # Mock conversation service
        model_service.conversation_service.get_conversation = AsyncMock(return_value=sample_conversation)
        model_service.conversation_service.add_message = AsyncMock(return_value=Mock(id=uuid4()))
        model_service.conversation_service.update_message_status = AsyncMock()

        # Mock database
        mock_db.get = AsyncMock(return_value=sample_app)

        # Mock provider
        mock_provider = AsyncMock()
        mock_response = ModelResponse(
            content="Test response",
            model="gpt-4",
            usage={"total_tokens": 50},
            finish_reason="stop",
            metadata={},
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        with patch.object(model_service, "_get_provider_from_app", return_value=mock_provider), patch.object(
            model_service,
            "_get_model_config_from_app",
            return_value=ModelConfig(model="gpt-4"),
        ):
            result = await model_service.generate_response(
                conversation_id=sample_conversation.id,
                user_message="Hello",
                stream=False,
            )

        assert isinstance(result, ModelResponse)
        assert result.content == "Test response"

    @pytest.mark.asyncio
    async def test_generate_response_app_not_found(self, model_service, sample_conversation, mock_db):
        """Test error when app is not found."""
        model_service.conversation_service.get_conversation = AsyncMock(return_value=sample_conversation)
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError, match="App not found"):
            await model_service.generate_response(
                conversation_id=sample_conversation.id,
                user_message="Hello",
                stream=False,
            )

    @pytest.mark.asyncio
    async def test_generate_response_streaming(self, model_service, sample_app, sample_conversation, mock_db):
        """Test streaming response."""
        model_service.conversation_service.get_conversation = AsyncMock(return_value=sample_conversation)
        model_service.conversation_service.add_message = AsyncMock(return_value=Mock(id=uuid4()))
        mock_db.get = AsyncMock(return_value=sample_app)

        # Mock provider with streaming
        mock_provider = AsyncMock()

        async def mock_stream():
            for chunk in ["Hello", " ", "World"]:
                yield chunk

        mock_provider.generate_stream = Mock(return_value=mock_stream())

        with patch.object(model_service, "_get_provider_from_app", return_value=mock_provider), patch.object(
            model_service,
            "_get_model_config_from_app",
            return_value=ModelConfig(model="gpt-4", stream=True),
        ):
            result = await model_service.generate_response(
                conversation_id=sample_conversation.id,
                user_message="Hello",
                stream=True,
            )

        # Result should be an async iterator
        assert hasattr(result, "__anext__")


class TestGenerateComplete:
    """Tests for _generate_complete method."""

    @pytest.mark.asyncio
    async def test_generate_complete_success(self, model_service):
        """Test successfully generating complete response."""
        mock_msg = Mock(id=uuid4())
        model_service.conversation_service.add_message = AsyncMock(return_value=mock_msg)
        model_service.conversation_service.update_message_status = AsyncMock()

        mock_provider = AsyncMock()
        mock_response = ModelResponse(
            content="Test response",
            model="gpt-4",
            usage={"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
            finish_reason="stop",
            metadata={},
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        config = ModelConfig(model="gpt-4")
        messages = [{"role": "user", "content": "Hello"}]

        result = await model_service._generate_complete(
            provider=mock_provider,
            config=config,
            messages=messages,
            conversation_id=uuid4(),
        )

        assert result == mock_response
        assert model_service.conversation_service.update_message_status.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_complete_with_error(self, model_service):
        """Test handling error during generation."""
        mock_msg = Mock(id=uuid4())
        model_service.conversation_service.add_message = AsyncMock(return_value=mock_msg)
        model_service.conversation_service.update_message_status = AsyncMock()

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("API Error"))

        config = ModelConfig(model="gpt-4")
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(Exception, match="API Error"):
            await model_service._generate_complete(
                provider=mock_provider,
                config=config,
                messages=messages,
                conversation_id=uuid4(),
            )

        # Verify message status was updated to FAILED
        calls = model_service.conversation_service.update_message_status.call_args_list
        assert any(MessageStatus.FAILED in str(call) for call in calls)


class TestGenerateStream:
    """Tests for _generate_stream method."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, model_service):
        """Test successfully generating streaming response."""
        mock_msg = Mock(id=uuid4())
        model_service.conversation_service.add_message = AsyncMock(return_value=mock_msg)
        model_service.conversation_service.update_message_status = AsyncMock()

        mock_provider = AsyncMock()

        async def mock_stream():
            for chunk in ["Hello", " ", "World"]:
                yield chunk

        mock_provider.generate_stream = Mock(return_value=mock_stream())

        config = ModelConfig(model="gpt-4", stream=True)
        messages = [{"role": "user", "content": "Hello"}]

        result_chunks = []
        async for chunk in model_service._generate_stream(
            provider=mock_provider,
            config=config,
            messages=messages,
            conversation_id=uuid4(),
        ):
            result_chunks.append(chunk)

        assert result_chunks == ["Hello", " ", "World"]
        assert model_service.conversation_service.update_message_status.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_stream_with_error(self, model_service):
        """Test handling error during streaming."""
        mock_msg = Mock(id=uuid4())
        model_service.conversation_service.add_message = AsyncMock(return_value=mock_msg)
        model_service.conversation_service.update_message_status = AsyncMock()

        mock_provider = AsyncMock()

        async def mock_stream():
            yield "Hello"
            raise Exception("Stream error")

        mock_provider.generate_stream = Mock(return_value=mock_stream())

        config = ModelConfig(model="gpt-4", stream=True)
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(Exception, match="Stream error"):
            async for _ in model_service._generate_stream(
                provider=mock_provider,
                config=config,
                messages=messages,
                conversation_id=uuid4(),
            ):
                pass

        # Verify message status was updated to FAILED
        calls = model_service.conversation_service.update_message_status.call_args_list
        assert any(MessageStatus.FAILED in str(call) for call in calls)


class TestValidateAppModelConfig:
    """Tests for validate_app_model_config method."""

    @pytest.mark.asyncio
    async def test_validate_config_success(self, model_service, sample_app):
        """Test successfully validating app model config."""
        mock_provider = AsyncMock()
        mock_provider.validate_credentials = AsyncMock(return_value=True)

        with patch.object(model_service, "_get_provider_from_app", return_value=mock_provider):
            result = await model_service.validate_app_model_config(sample_app)

        assert result is True
        mock_provider.validate_credentials.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_config_invalid(self, model_service, sample_app):
        """Test validation failure."""
        mock_provider = AsyncMock()
        mock_provider.validate_credentials = AsyncMock(return_value=False)

        with patch.object(model_service, "_get_provider_from_app", return_value=mock_provider):
            result = await model_service.validate_app_model_config(sample_app)

        assert result is False
