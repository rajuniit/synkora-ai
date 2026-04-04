"""Redis configuration with Sentinel and Cluster support for Kubernetes HA."""

import logging
import os

import redis
from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings
from redis.sentinel import Sentinel

logger = logging.getLogger(__name__)


class RedisConfig(BaseSettings):
    """Redis configuration settings."""

    redis_url: RedisDsn | None = Field(
        default=None,
        description=(
            "Redis connection URL (e.g. redis://localhost:6379/0). "
            "Not required when REDIS_SENTINEL_HOSTS is set — Sentinel mode "
            "discovers the master automatically and ignores this field. "
            "Required in standalone mode."
        ),
    )

    redis_max_connections: int = Field(
        default=50,
        description="Max Redis connections per process. Scale this based on your deployment (e.g., 50 per pod with 4 pods = 200 total).",
    )

    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string."""
        return str(self.redis_url)


# Global Redis clients
_redis_client = None
_redis_async_client = None
# Track which event loop created _redis_async_client so we can detect loop changes
# (e.g. pytest creates a fresh loop per test; reusing a client from a closed loop
# causes "Event loop is closed" errors).
_redis_async_client_loop = None


def _parse_sentinel_hosts(hosts_str: str) -> list[tuple[str, int]]:
    """
    Parse Sentinel hosts from comma-separated string.

    Args:
        hosts_str: Format: "host1:port1,host2:port2,host3:port3"

    Returns:
        List of (host, port) tuples
    """
    hosts = []
    for host_port in hosts_str.split(","):
        host_port = host_port.strip()
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            hosts.append((host, int(port)))
        else:
            hosts.append((host_port, 26379))  # Default Sentinel port
    return hosts


def get_redis() -> redis.Redis:
    """
    Get or create Redis client connection.

    Supports three modes:
    1. Sentinel mode: Set REDIS_SENTINEL_HOSTS and REDIS_MASTER_NAME
    2. Cluster mode: Set REDIS_CLUSTER_HOSTS (not implemented, use redis-py-cluster)
    3. Standard mode: Use REDIS_URL

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            from src.config.settings import settings

            # Check for Sentinel configuration (Kubernetes HA)
            sentinel_hosts = os.getenv("REDIS_SENTINEL_HOSTS")
            master_name = os.getenv("REDIS_MASTER_NAME", "mymaster")

            if sentinel_hosts:
                # Sentinel mode for Kubernetes HA
                hosts = _parse_sentinel_hosts(sentinel_hosts)
                sentinel_password = os.getenv("REDIS_SENTINEL_PASSWORD")
                redis_password = os.getenv("REDIS_PASSWORD")

                sentinel = Sentinel(
                    hosts,
                    sentinel_kwargs={
                        "password": sentinel_password,
                    }
                    if sentinel_password
                    else {},
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                )

                # Get master connection with connection pool
                _redis_client = sentinel.master_for(
                    master_name,
                    socket_timeout=5.0,
                    password=redis_password,
                    decode_responses=True,
                    max_connections=settings.redis_max_connections,
                )

                logger.info(f"Redis Sentinel connected to master '{master_name}' via {hosts}")
            else:
                # Standard mode
                if not settings.redis_url:
                    raise ValueError(
                        "REDIS_URL is required when REDIS_SENTINEL_HOSTS is not set. "
                        "Set REDIS_URL=redis://host:6379/0 in your environment."
                    )
                redis_url = str(settings.redis_url)

                # Create connection pool with retry
                pool = redis.ConnectionPool.from_url(
                    redis_url,
                    decode_responses=True,
                    max_connections=settings.redis_max_connections,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )

                _redis_client = redis.Redis(connection_pool=pool)
                logger.info(f"Redis connected at {redis_url}")

            # Test connection
            _redis_client.ping()
            logger.info("Redis connection verified successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    return _redis_client


def close_redis():
    """Close Redis connection and cleanup pool."""
    global _redis_client
    if _redis_client:
        try:
            # Close the connection pool
            if hasattr(_redis_client, "connection_pool"):
                _redis_client.connection_pool.disconnect()
            _redis_client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
            logger.info("Redis connection closed")


def get_redis_async():
    """
    Get or create async Redis client for async contexts.

    Returns a cached client instance — does NOT create a new pool on every call.

    The client is recreated whenever the running event loop changes. In production
    there is only one long-lived loop, so the singleton is reused indefinitely.
    In test environments (pytest-asyncio creates a fresh loop per test) the client
    is transparently rebuilt for each new loop, avoiding "Event loop is closed" errors.

    Returns:
        Async Redis client instance
    """
    global _redis_async_client, _redis_async_client_loop

    import asyncio

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    # Recreate if no client yet, or if the event loop has changed / been closed.
    if _redis_async_client is None or (
        _redis_async_client_loop is not None and _redis_async_client_loop is not current_loop
    ):
        _redis_async_client = None  # drop the stale reference

    if _redis_async_client is not None:
        return _redis_async_client

    import redis.asyncio as aioredis

    from src.config.settings import settings

    sentinel_hosts = os.getenv("REDIS_SENTINEL_HOSTS")
    master_name = os.getenv("REDIS_MASTER_NAME", "mymaster")

    if sentinel_hosts:
        from redis.asyncio.sentinel import Sentinel as AsyncSentinel

        hosts = _parse_sentinel_hosts(sentinel_hosts)
        sentinel_password = os.getenv("REDIS_SENTINEL_PASSWORD")
        redis_password = os.getenv("REDIS_PASSWORD")

        sentinel = AsyncSentinel(
            hosts,
            sentinel_kwargs={
                "password": sentinel_password,
            }
            if sentinel_password
            else {},
        )

        _redis_async_client = sentinel.master_for(
            master_name,
            password=redis_password,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )
    else:
        if not settings.redis_url:
            raise ValueError(
                "REDIS_URL is required when REDIS_SENTINEL_HOSTS is not set. "
                "Set REDIS_URL=redis://host:6379/0 in your environment."
            )
        redis_url = str(settings.redis_url)
        _redis_async_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )

    _redis_async_client_loop = current_loop
    return _redis_async_client


async def close_redis_async():
    """Close async Redis connection and cleanup."""
    global _redis_async_client, _redis_async_client_loop
    client = _redis_async_client
    _redis_async_client = None
    _redis_async_client_loop = None
    if client:
        try:
            await client.aclose()
        except Exception as e:
            logger.warning(f"Error closing async Redis connection: {e}")
        logger.info("Async Redis connection closed")
