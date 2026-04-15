"""
Shared HTTP client pool for OAuth providers.

Provides singleton httpx.AsyncClient instances with proper connection pooling,
timeouts, retry configuration with exponential backoff for high-load scalability.
"""

import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default timeout for all OAuth API calls (seconds)
DEFAULT_TIMEOUT = 30.0

# Connection pool limits
MAX_CONNECTIONS = 100
MAX_KEEPALIVE_CONNECTIONS = 20

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0  # seconds
DEFAULT_RETRY_MAX_DELAY = 30.0  # seconds
DEFAULT_RETRY_JITTER = 0.5  # 50% jitter

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# Global client instances
_httpx_client: httpx.AsyncClient | None = None
_aiohttp_session: Any | None = None
_client_lock = asyncio.Lock()


def is_retryable_error(error: Exception) -> bool:
    """Check if an error should trigger a retry."""
    if isinstance(error, httpx.TimeoutException):
        return True
    if isinstance(error, httpx.ConnectError):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES
    return False


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    jitter: float = DEFAULT_RETRY_JITTER,
) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Jitter factor (0.5 = +/- 50%)

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = min(base_delay * (2**attempt), max_delay)
    # Add jitter to prevent thundering herd
    jitter_range = delay * jitter
    delay = delay + random.uniform(-jitter_range, jitter_range)
    return max(0, delay)


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    max_delay: float = DEFAULT_RETRY_MAX_DELAY,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for async functions that adds exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if not is_retryable_error(e):
                        # Non-retryable error, raise immediately
                        raise

                    if attempt >= max_retries:
                        # Max retries exceeded
                        logger.warning(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise

                    delay = calculate_backoff_delay(attempt, base_delay, max_delay)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


def get_default_timeout() -> httpx.Timeout:
    """Get default timeout configuration."""
    return httpx.Timeout(
        connect=10.0,  # Connection timeout
        read=DEFAULT_TIMEOUT,  # Read timeout
        write=DEFAULT_TIMEOUT,  # Write timeout
        pool=10.0,  # Pool timeout
    )


def get_connection_limits() -> httpx.Limits:
    """Get connection pool limits."""
    return httpx.Limits(
        max_connections=MAX_CONNECTIONS,
        max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
        keepalive_expiry=30.0,  # Keep connections alive for 30 seconds
    )


async def get_httpx_client() -> httpx.AsyncClient:
    """
    Get the shared httpx AsyncClient instance.

    Returns a singleton client with connection pooling configured for
    high-throughput OAuth API calls.
    """
    global _httpx_client

    if _httpx_client is None:
        async with _client_lock:
            if _httpx_client is None:
                _httpx_client = httpx.AsyncClient(
                    timeout=get_default_timeout(),
                    limits=get_connection_limits(),
                    http2=True,  # Enable HTTP/2 for better performance
                    follow_redirects=True,
                )
                logger.info("Initialized shared httpx client pool")

    return _httpx_client


async def get_aiohttp_session():
    """
    Get the shared aiohttp ClientSession instance.

    Returns a singleton session with connection pooling for providers
    that require aiohttp (e.g., Zoom, Google Calendar).
    """
    global _aiohttp_session

    if _aiohttp_session is None:
        async with _client_lock:
            if _aiohttp_session is None:
                try:
                    import aiohttp

                    connector = aiohttp.TCPConnector(
                        limit=MAX_CONNECTIONS,
                        limit_per_host=20,
                        ttl_dns_cache=300,  # Cache DNS for 5 minutes
                        keepalive_timeout=30,
                    )
                    timeout = aiohttp.ClientTimeout(
                        total=DEFAULT_TIMEOUT,
                        connect=10.0,
                        sock_read=DEFAULT_TIMEOUT,
                    )
                    _aiohttp_session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                    )
                    logger.info("Initialized shared aiohttp session pool")
                except ImportError:
                    logger.warning("aiohttp not installed, some OAuth providers may not work")
                    return None

    return _aiohttp_session


async def close_http_clients():
    """
    Close all HTTP client pools.

    Should be called during application shutdown.
    """
    global _httpx_client, _aiohttp_session

    async with _client_lock:
        if _httpx_client is not None:
            await _httpx_client.aclose()
            _httpx_client = None
            logger.info("Closed httpx client pool")

        if _aiohttp_session is not None:
            await _aiohttp_session.close()
            _aiohttp_session = None
            logger.info("Closed aiohttp session pool")


class HTTPClientMixin:
    """
    Mixin class for OAuth providers to use shared HTTP clients.

    Provides helper methods for making HTTP requests with proper
    error handling, timeouts, and exponential backoff retry logic.
    """

    # Retry configuration (can be overridden by subclasses)
    _max_retries: int = DEFAULT_MAX_RETRIES
    _retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY
    _retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY

    async def _get_client(self) -> httpx.AsyncClient:
        """Get the shared httpx client."""
        return await get_httpx_client()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        timeout: float | None = None,
        retry: bool = True,
        max_retries: int | None = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with the shared client and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            timeout: Optional custom timeout (uses default if not specified)
            retry: Whether to retry on transient failures (default: True)
            max_retries: Override default max retries
            **kwargs: Additional arguments passed to httpx request

        Returns:
            httpx.Response object

        Raises:
            httpx.TimeoutException: If request times out after all retries
            httpx.HTTPStatusError: If response has non-retryable error status
        """
        client = await self._get_client()

        if timeout is not None:
            kwargs["timeout"] = timeout

        if not retry:
            # No retry, just make the request
            return await client.request(method, url, **kwargs)

        # Retry with exponential backoff
        retries = max_retries if max_retries is not None else self._max_retries
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                response = await client.request(method, url, **kwargs)

                # Check for retryable status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt >= retries:
                        # Return the response even with error status on last attempt
                        return response

                    delay = calculate_backoff_delay(attempt, self._retry_base_delay, self._retry_max_delay)
                    logger.info(
                        f"Retrying {method} {url} in {delay:.2f}s "
                        f"(status {response.status_code}, attempt {attempt + 1}/{retries})"
                    )
                    await asyncio.sleep(delay)
                    continue

                return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e

                if attempt >= retries:
                    logger.warning(f"Max retries ({retries}) exceeded for {method} {url}: {e}")
                    raise

                delay = calculate_backoff_delay(attempt, self._retry_base_delay, self._retry_max_delay)
                logger.info(f"Retrying {method} {url} in {delay:.2f}s (attempt {attempt + 1}/{retries}): {e}")
                await asyncio.sleep(delay)

        # Should not reach here
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected retry loop exit")

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request with retry."""
        return await self._request("GET", url, **kwargs)

    async def _post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request with retry."""
        return await self._request("POST", url, **kwargs)

    async def _put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request with retry."""
        return await self._request("PUT", url, **kwargs)

    async def _delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request with retry."""
        return await self._request("DELETE", url, **kwargs)
