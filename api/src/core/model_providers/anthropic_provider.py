"""
Anthropic model provider implementation.

Provides integration with Anthropic's API for Claude models.
"""

import json
from collections.abc import AsyncIterator

import httpx

from .base import BaseModelProvider, ModelConfig, ModelProviderType, ModelResponse


class AnthropicProvider(BaseModelProvider):
    """Anthropic model provider."""

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        self.base_url = kwargs.get("base_url", self.BASE_URL)

    @property
    def provider_type(self) -> ModelProviderType:
        """Get provider type."""
        return ModelProviderType.ANTHROPIC

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

    def _convert_messages(self, messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        """
        Convert messages to Anthropic format.

        Anthropic requires system message separate from conversation.

        Args:
            messages: Standard message format

        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = ""
        conversation = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )

        return system_message, conversation

    async def generate(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> ModelResponse:
        """
        Generate a response using Anthropic API.

        Args:
            messages: List of message dicts
            config: Model configuration

        Returns:
            Model response

        Raises:
            httpx.HTTPError: If API request fails
        """
        self.validate_config(config)

        system_message, conversation = self._convert_messages(messages)

        payload = {
            "model": config.model,
            "messages": conversation,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }

        if system_message:
            payload["system"] = system_message

        if config.stop:
            payload["stop_sequences"] = config.stop

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        content = data["content"][0]["text"]
        usage = data.get("usage", {})

        return ModelResponse(
            content=content,
            model=data["model"],
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
            finish_reason=data.get("stop_reason", "end_turn"),
            metadata={
                "id": data.get("id"),
                "type": data.get("type"),
                "role": data.get("role"),
            },
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response using Anthropic API.

        Args:
            messages: List of message dicts
            config: Model configuration

        Yields:
            Content chunks

        Raises:
            httpx.HTTPError: If API request fails
        """
        self.validate_config(config)

        system_message, conversation = self._convert_messages(messages)

        payload = {
            "model": config.model,
            "messages": conversation,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        if config.stop:
            payload["stop_sequences"] = config.stop

        async with (
            httpx.AsyncClient() as client,
            client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=payload,
                timeout=60.0,
            ) as response,
        ):
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                try:
                    data = json.loads(line[6:])

                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")

                except json.JSONDecodeError:
                    continue

    async def validate_credentials(self) -> bool:
        """
        Validate Anthropic API credentials.

        Returns:
            True if credentials are valid

        Raises:
            httpx.HTTPError: If validation fails
        """
        try:
            # Make a minimal request to validate credentials
            payload = {
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    def get_available_models(self) -> list[str]:
        """
        Get list of available Anthropic models.

        Returns:
            List of model identifiers
        """
        return [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
            "claude-opus-4-1",
            "claude-opus-4",
            "claude-sonnet-4",
            "claude-3.7-sonnet",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2",
        ]

    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for Anthropic models.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        # Anthropic uses similar tokenization to OpenAI
        return len(text) // 4
