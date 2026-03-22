"""
Base model provider interface.

Defines the abstract interface that all model providers must implement.
"""

import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


class ModelProviderType(enum.StrEnum):
    """Model provider types."""

    OPENAI = "OPENAI"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


@dataclass
class ModelResponse:
    """
    Response from a model provider.

    Attributes:
        content: Generated text content
        model: Model name used
        usage: Token usage information
        finish_reason: Reason for completion
        metadata: Additional metadata
    """

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str
    metadata: dict[str, Any]


@dataclass
class ModelConfig:
    """
    Configuration for model inference.

    Attributes:
        model: Model name/identifier
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty (-2 to 2)
        presence_penalty: Presence penalty (-2 to 2)
        stop: Stop sequences
        stream: Whether to stream responses
    """

    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    stream: bool = False


class BaseModelProvider(ABC):
    """
    Abstract base class for model providers.

    All model providers must implement this interface to ensure
    consistent behavior across different providers.
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs

    @property
    @abstractmethod
    def provider_type(self) -> ModelProviderType:
        """Get the provider type."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> ModelResponse:
        """
        Generate a response from the model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            config: Model configuration

        Returns:
            Model response

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            config: Model configuration

        Yields:
            Content chunks as they are generated

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate the provider credentials.

        Returns:
            True if credentials are valid

        Raises:
            Exception: If validation fails
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """
        Get list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a simple estimation. Providers should override
        with more accurate implementations.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    def validate_config(self, config: ModelConfig) -> None:
        """
        Validate model configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if config.temperature < 0 or config.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if config.max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        if config.top_p < 0 or config.top_p > 1:
            raise ValueError("top_p must be between 0 and 1")

        if config.frequency_penalty < -2 or config.frequency_penalty > 2:
            raise ValueError("frequency_penalty must be between -2 and 2")

        if config.presence_penalty < -2 or config.presence_penalty > 2:
            raise ValueError("presence_penalty must be between -2 and 2")
