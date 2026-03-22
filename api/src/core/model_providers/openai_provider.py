"""
OpenAI model provider implementation.

Provides integration with OpenAI's API for GPT models.
"""

import json
from collections.abc import AsyncIterator

import httpx

from .base import BaseModelProvider, ModelConfig, ModelProviderType, ModelResponse


class OpenAIProvider(BaseModelProvider):
    """OpenAI model provider."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        self.organization = kwargs.get("organization")
        self.base_url = kwargs.get("base_url", self.BASE_URL)

    @property
    def provider_type(self) -> ModelProviderType:
        """Get provider type."""
        return ModelProviderType.OPENAI

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    async def generate(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> ModelResponse:
        """
        Generate a response using OpenAI API.

        Args:
            messages: List of message dicts
            config: Model configuration

        Returns:
            Model response

        Raises:
            httpx.HTTPError: If API request fails
        """
        self.validate_config(config)

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
        }

        if config.stop:
            payload["stop"] = config.stop

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return ModelResponse(
            content=choice["message"]["content"],
            model=data["model"],
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            finish_reason=choice.get("finish_reason", "stop"),
            metadata={
                "id": data.get("id"),
                "created": data.get("created"),
                "system_fingerprint": data.get("system_fingerprint"),
            },
        )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        config: ModelConfig,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response using OpenAI API.

        Args:
            messages: List of message dicts
            config: Model configuration

        Yields:
            Content chunks

        Raises:
            httpx.HTTPError: If API request fails
        """
        self.validate_config(config)

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": True,
        }

        if config.stop:
            payload["stop"] = config.stop

        async with (
            httpx.AsyncClient() as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=60.0,
            ) as response,
        ):
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or line == "data: [DONE]":
                    continue

                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def validate_credentials(self) -> bool:
        """
        Validate OpenAI API credentials.

        Returns:
            True if credentials are valid

        Raises:
            httpx.HTTPError: If validation fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            return False

    def get_available_models(self) -> list[str]:
        """
        Get list of available OpenAI models.

        Returns:
            List of model identifiers
        """
        return [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-4-32k",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]

    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for OpenAI models.

        This is a rough estimation. For accurate counts,
        use tiktoken library.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English
        # This should be replaced with tiktoken for accuracy
        return len(text) // 4
