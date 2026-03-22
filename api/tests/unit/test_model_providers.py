"""
Unit tests for model providers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.errors import ValidationError
from src.core.model_providers import (
    AnthropicProvider,
    BaseModelProvider,
    ModelConfig,
    ModelProviderFactory,
    ModelProviderType,
    ModelResponse,
    OpenAIProvider,
)


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_model_config_defaults(self):
        """Test default values."""
        config = ModelConfig(model="gpt-4")

        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.top_p == 1.0
        assert config.frequency_penalty == 0.0
        assert config.presence_penalty == 0.0
        assert config.stop is None
        assert config.stream is False

    def test_model_config_custom_values(self):
        """Test custom values."""
        config = ModelConfig(
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stop=["END"],
            stream=True,
        )

        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 500
        assert config.top_p == 0.9
        assert config.frequency_penalty == 0.5
        assert config.presence_penalty == 0.5
        assert config.stop == ["END"]
        assert config.stream is True


class TestBaseModelProvider:
    """Test BaseModelProvider validation."""

    def test_validate_config_valid(self):
        """Test validation with valid config."""
        provider = OpenAIProvider(api_key="test-key")
        config = ModelConfig(model="gpt-4")

        # Should not raise
        provider.validate_config(config)

    def test_validate_config_invalid_temperature(self):
        """Test validation with invalid temperature."""
        provider = OpenAIProvider(api_key="test-key")
        config = ModelConfig(model="gpt-4", temperature=3.0)

        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            provider.validate_config(config)

    def test_validate_config_invalid_max_tokens(self):
        """Test validation with invalid max_tokens."""
        provider = OpenAIProvider(api_key="test-key")
        config = ModelConfig(model="gpt-4", max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be positive"):
            provider.validate_config(config)

    def test_validate_config_invalid_top_p(self):
        """Test validation with invalid top_p."""
        provider = OpenAIProvider(api_key="test-key")
        config = ModelConfig(model="gpt-4", top_p=1.5)

        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            provider.validate_config(config)

    def test_calculate_tokens(self):
        """Test token calculation."""
        provider = OpenAIProvider(api_key="test-key")
        text = "This is a test message"

        tokens = provider.calculate_tokens(text)
        assert tokens > 0
        assert tokens == len(text) // 4


class TestOpenAIProvider:
    """Test OpenAI provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = OpenAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.provider_type == ModelProviderType.OPENAI
        assert provider.base_url == "https://api.openai.com/v1"

    def test_initialization_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        provider = OpenAIProvider(api_key="test-key", base_url="https://custom.openai.com/v1")

        assert provider.base_url == "https://custom.openai.com/v1"

    def test_get_available_models(self):
        """Test getting available models."""
        provider = OpenAIProvider(api_key="test-key")
        models = provider.get_available_models()

        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models
        assert len(models) > 0

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test-id",
            "model": "gpt-4",
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            config = ModelConfig(model="gpt-4")
            messages = [{"role": "user", "content": "Hi"}]

            response = await provider.generate(messages, config)

            assert isinstance(response, ModelResponse)
            assert response.content == "Hello!"
            assert response.model == "gpt-4"
            assert response.usage["total_tokens"] == 15


class TestAnthropicProvider:
    """Test Anthropic provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = AnthropicProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.provider_type == ModelProviderType.ANTHROPIC
        assert provider.base_url == "https://api.anthropic.com/v1"

    def test_get_available_models(self):
        """Test getting available models."""
        provider = AnthropicProvider(api_key="test-key")
        models = provider.get_available_models()

        assert "claude-3-opus-20240229" in models
        assert "claude-3-sonnet-20240229" in models
        assert len(models) > 0

    def test_convert_messages(self):
        """Test message conversion."""
        provider = AnthropicProvider(api_key="test-key")

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]

        system, conversation = provider._convert_messages(messages)

        assert system == "You are helpful"
        assert len(conversation) == 2
        assert conversation[0]["role"] == "user"
        assert conversation[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        provider = AnthropicProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test-id",
            "model": "claude-3-sonnet-20240229",
            "content": [{"text": "Hello!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            config = ModelConfig(model="claude-3-sonnet-20240229")
            messages = [{"role": "user", "content": "Hi"}]

            response = await provider.generate(messages, config)

            assert isinstance(response, ModelResponse)
            assert response.content == "Hello!"
            assert response.model == "claude-3-sonnet-20240229"
            assert response.usage["total_tokens"] == 15


class TestModelProviderFactory:
    """Test ModelProviderFactory."""

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = ModelProviderFactory.create(ModelProviderType.OPENAI, api_key="test-key")

        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = ModelProviderFactory.create(ModelProviderType.ANTHROPIC, api_key="test-key")

        assert isinstance(provider, AnthropicProvider)
        assert provider.api_key == "test-key"

    def test_create_from_config(self):
        """Test creating provider from config."""
        config = {"provider": "OPENAI", "api_key": "test-key", "organization": "test-org"}

        provider = ModelProviderFactory.create_from_config(config)

        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"
        assert provider.organization == "test-org"

    def test_create_from_config_missing_provider(self):
        """Test creating from config without provider."""
        config = {"api_key": "test-key"}

        with pytest.raises(ValidationError) as exc_info:
            ModelProviderFactory.create_from_config(config)

        assert "Provider type not specified" in exc_info.value.message

    def test_create_from_config_missing_api_key(self):
        """Test creating from config without API key."""
        config = {"provider": "OPENAI"}

        with pytest.raises(ValidationError) as exc_info:
            ModelProviderFactory.create_from_config(config)

        assert "API key not specified" in exc_info.value.message

    def test_create_from_config_invalid_provider(self):
        """Test creating from config with invalid provider."""
        config = {"provider": "invalid", "api_key": "test-key"}

        with pytest.raises(ValidationError) as exc_info:
            ModelProviderFactory.create_from_config(config)

        assert "Invalid provider type" in exc_info.value.message

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = ModelProviderFactory.get_supported_providers()

        assert "OPENAI" in providers
        assert "anthropic" in providers
        assert len(providers) >= 2

    def test_register_provider(self):
        """Test registering a custom provider."""

        class CustomProvider(BaseModelProvider):
            @property
            def provider_type(self):
                return ModelProviderType.LOCAL

            async def generate(self, messages, config):
                pass

            async def generate_stream(self, messages, config):
                pass

            async def validate_credentials(self):
                return True

            def get_available_models(self):
                return ["custom-model"]

        ModelProviderFactory.register_provider(ModelProviderType.LOCAL, CustomProvider)

        provider = ModelProviderFactory.create(ModelProviderType.LOCAL, api_key="test")

        assert isinstance(provider, CustomProvider)
