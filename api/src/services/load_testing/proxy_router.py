"""
LLM Proxy Router

Routes incoming LLM requests to appropriate mock providers.
"""

import logging
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.proxy_config import ProxyConfig, ProxyProvider

from .mock_providers import (
    AnthropicMockProvider,
    BaseMockProvider,
    GoogleMockProvider,
    OpenAIMockProvider,
)
from .mock_providers.base import MockError

logger = logging.getLogger(__name__)


class LLMProxyRouter:
    """
    Routes LLM requests to mock providers based on configuration.

    Handles API key validation, rate limiting, and provider selection.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the router.

        Args:
            db: Database session for config lookup
        """
        self.db = db
        self._provider_cache: dict[str, tuple[ProxyConfig, BaseMockProvider]] = {}

    async def get_provider(self, api_key: str) -> tuple[ProxyConfig, BaseMockProvider]:
        """
        Get the provider for an API key.

        Args:
            api_key: The API key from the request

        Returns:
            tuple: (ProxyConfig, MockProvider instance)

        Raises:
            HTTPException: If API key is invalid or inactive
        """
        # Check cache first
        key_hash = ProxyConfig.hash_api_key(api_key)
        if key_hash in self._provider_cache:
            return self._provider_cache[key_hash]

        # Look up config
        result = await self.db.execute(select(ProxyConfig).filter(ProxyConfig.api_key_hash == key_hash))
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not config.is_active:
            raise HTTPException(status_code=403, detail="API key is inactive")

        # Create provider
        provider = self._create_provider(config)

        # Cache
        self._provider_cache[key_hash] = (config, provider)

        return config, provider

    def _create_provider(self, config: ProxyConfig) -> BaseMockProvider:
        """
        Create the appropriate mock provider.

        Args:
            config: Proxy configuration

        Returns:
            BaseMockProvider: The mock provider instance
        """
        mock_config = config.mock_config or config.default_mock_config

        if config.provider == ProxyProvider.OPENAI:
            return OpenAIMockProvider(mock_config)
        elif config.provider == ProxyProvider.ANTHROPIC:
            return AnthropicMockProvider(mock_config)
        elif config.provider == ProxyProvider.GOOGLE:
            return GoogleMockProvider(mock_config)
        elif config.provider == ProxyProvider.AZURE_OPENAI:
            # Azure OpenAI uses same format as OpenAI
            return OpenAIMockProvider(mock_config)
        else:
            # Default to OpenAI format
            return OpenAIMockProvider(mock_config)

    async def check_rate_limit(self, config: ProxyConfig) -> bool:
        """
        Check if request is within rate limits.

        Args:
            config: Proxy configuration

        Returns:
            bool: True if within limits

        Raises:
            HTTPException: If rate limit exceeded
        """
        from src.config.redis import get_redis

        redis = get_redis()
        key = f"proxy:{config.id}:ratelimit"

        # Get current count
        current = redis.get(key)
        if current and int(current) >= config.rate_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "1"},
            )

        # Increment with 1-second expiry
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 1)
        pipe.execute()

        return True

    async def track_usage(self, config: ProxyConfig, tokens: int = 0) -> None:
        """
        Track usage for a proxy request.

        Args:
            config: Proxy configuration
            tokens: Number of tokens generated
        """
        from datetime import timedelta

        from src.config.redis import get_redis

        redis = get_redis()

        # Update in-memory counters
        config.usage_count += 1
        config.total_tokens_generated += tokens

        # Update Redis counters for real-time stats
        pipe = redis.pipeline()

        # Hourly counter
        hour_key = f"proxy:{config.id}:requests:hour"
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)

        # Daily counter
        day_key = f"proxy:{config.id}:requests:day"
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)

        pipe.execute()

        # Commit DB changes
        await self.db.commit()

    async def track_error(self, config: ProxyConfig) -> None:
        """
        Track an error for a proxy request.

        Args:
            config: Proxy configuration
        """
        from src.config.redis import get_redis

        redis = get_redis()

        # Update Redis error counter
        error_key = f"proxy:{config.id}:errors:day"
        pipe = redis.pipeline()
        pipe.incr(error_key)
        pipe.expire(error_key, 86400)
        pipe.execute()

    async def handle_chat_completion(
        self, api_key: str, request_body: dict, stream: bool = False
    ) -> dict | AsyncGenerator[str, None]:
        """
        Handle an OpenAI-compatible chat completion request.

        Args:
            api_key: The API key from the request
            request_body: The request body
            stream: Whether to stream the response

        Returns:
            dict or AsyncGenerator: Response or stream
        """
        config, provider = await self.get_provider(api_key)
        await self.check_rate_limit(config)

        try:
            if stream or request_body.get("stream", False):
                return await self._stream_response(config, provider, request_body)
            else:
                response = await provider.generate_response(request_body)
                tokens = response.get("usage", {}).get("completion_tokens", 0)
                await self.track_usage(config, tokens)
                return response

        except MockError as e:
            await self.track_error(config)
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            await self.track_error(config)
            logger.error(f"Proxy error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_anthropic_messages(
        self, api_key: str, request_body: dict, stream: bool = False
    ) -> dict | AsyncGenerator[str, None]:
        """
        Handle an Anthropic-compatible messages request.

        Args:
            api_key: The API key from the request
            request_body: The request body
            stream: Whether to stream the response

        Returns:
            dict or AsyncGenerator: Response or stream
        """
        config, provider = await self.get_provider(api_key)
        await self.check_rate_limit(config)

        # Force Anthropic provider
        if not isinstance(provider, AnthropicMockProvider):
            provider = AnthropicMockProvider(config.mock_config or config.default_mock_config)

        try:
            if stream or request_body.get("stream", False):
                return await self._stream_response(config, provider, request_body)
            else:
                response = await provider.generate_response(request_body)
                tokens = response.get("usage", {}).get("output_tokens", 0)
                await self.track_usage(config, tokens)
                return response

        except MockError as e:
            await self.track_error(config)
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            await self.track_error(config)
            logger.error(f"Proxy error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_google_generate(
        self, api_key: str, model: str, request_body: dict, stream: bool = False
    ) -> dict | AsyncGenerator[str, None]:
        """
        Handle a Google Generative AI request.

        Args:
            api_key: The API key from the request
            model: The model name from the URL
            request_body: The request body
            stream: Whether to stream the response

        Returns:
            dict or AsyncGenerator: Response or stream
        """
        config, provider = await self.get_provider(api_key)
        await self.check_rate_limit(config)

        # Force Google provider
        if not isinstance(provider, GoogleMockProvider):
            provider = GoogleMockProvider(config.mock_config or config.default_mock_config)

        try:
            if stream:
                return await self._stream_response(config, provider, request_body)
            else:
                response = await provider.generate_response(request_body)
                tokens = response.get("usageMetadata", {}).get("candidatesTokenCount", 0)
                await self.track_usage(config, tokens)
                return response

        except MockError as e:
            await self.track_error(config)
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            await self.track_error(config)
            logger.error(f"Proxy error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def _stream_response(
        self,
        config: ProxyConfig,
        provider: BaseMockProvider,
        request_body: dict,
    ) -> AsyncGenerator[str, None]:
        """
        Generate and track a streaming response.

        Args:
            config: Proxy configuration
            provider: Mock provider
            request_body: Request body

        Yields:
            str: Response chunks
        """
        token_count = 0

        async def counted_stream():
            nonlocal token_count
            async for chunk in provider.generate_stream(request_body):
                # Estimate tokens from chunk
                if "content" in chunk or "text" in chunk:
                    token_count += 1
                yield chunk

            # Track usage after stream completes
            await self.track_usage(config, token_count)

        return counted_stream()

    async def get_models(self, api_key: str) -> dict:
        """
        Get available models for the proxy.

        Args:
            api_key: The API key

        Returns:
            dict: Models list response
        """
        config, provider = await self.get_provider(api_key)

        if isinstance(provider, OpenAIMockProvider):
            return provider.get_models_list()
        else:
            # Return generic list
            return {
                "object": "list",
                "data": [{"id": "mock-model", "object": "model", "owned_by": "synkora"}],
            }
