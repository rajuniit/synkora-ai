"""
Connection pool manager for vector databases.

Provides connection pooling to avoid creating new connections on every request.
Supports multiple vector DB providers with configurable pool sizes.

Uses the shared CircuitBreaker from circuit_breaker.py for fault tolerance.
"""

import logging
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any

from src.models.knowledge_base import VectorDBProvider as VectorDBProviderEnum
from src.services.performance.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)


# Alias for backwards compatibility
CircuitOpenError = CircuitBreakerOpen


@dataclass
class PooledConnection:
    """Wrapper for a pooled vector DB connection."""

    provider: Any
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0

    def mark_used(self):
        """Mark connection as used."""
        self.last_used = time.time()
        self.use_count += 1


@dataclass
class PoolStats:
    """Statistics for a connection pool."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0


class VectorDBConnectionPool:
    """
    Connection pool for vector database providers.

    Maintains a pool of connections per provider configuration to avoid
    connection overhead on every request.

    Features:
    - Configurable pool size per provider
    - Connection health checks
    - Automatic connection recycling
    - Thread-safe operations
    - Circuit breaker for fault tolerance
    """

    DEFAULT_POOL_SIZE = 5
    DEFAULT_MAX_IDLE_TIME = 300  # 5 minutes
    DEFAULT_MAX_CONNECTION_AGE = 3600  # 1 hour
    DEFAULT_CIRCUIT_FAILURE_THRESHOLD = 5
    DEFAULT_CIRCUIT_RECOVERY_TIMEOUT = 30.0

    def __init__(
        self,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_idle_time: int = DEFAULT_MAX_IDLE_TIME,
        max_connection_age: int = DEFAULT_MAX_CONNECTION_AGE,
        circuit_failure_threshold: int = DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
        circuit_recovery_timeout: float = DEFAULT_CIRCUIT_RECOVERY_TIMEOUT,
    ):
        """
        Initialize the connection pool.

        Args:
            pool_size: Maximum connections per provider config
            max_idle_time: Maximum idle time before connection is recycled
            max_connection_age: Maximum age of a connection before forced recycle
            circuit_failure_threshold: Failures before circuit opens
            circuit_recovery_timeout: Seconds before circuit tries half-open
        """
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self.max_connection_age = max_connection_age
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_recovery_timeout = circuit_recovery_timeout

        # Pools indexed by config hash
        self._pools: dict[str, Queue] = defaultdict(lambda: Queue(maxsize=pool_size))
        self._active: dict[str, int] = defaultdict(int)
        self._stats: dict[str, PoolStats] = defaultdict(PoolStats)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

        logger.info(
            f"VectorDB connection pool initialized: "
            f"pool_size={pool_size}, max_idle={max_idle_time}s, max_age={max_connection_age}s, "
            f"circuit_threshold={circuit_failure_threshold}, circuit_timeout={circuit_recovery_timeout}s"
        )

    def _get_circuit_breaker(self, config_key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a config."""
        if config_key not in self._circuit_breakers:
            with self._lock:
                if config_key not in self._circuit_breakers:
                    self._circuit_breakers[config_key] = CircuitBreaker(
                        name=f"vectordb:{config_key}",
                        failure_threshold=self.circuit_failure_threshold,
                        recovery_timeout=int(self.circuit_recovery_timeout),
                    )
        return self._circuit_breakers[config_key]

    def _get_config_key(self, provider_type: VectorDBProviderEnum, config: dict[str, Any]) -> str:
        """Generate a unique key for a provider configuration."""
        # Create a hashable key from provider type and config
        config_items = sorted(
            (k, str(v))
            for k, v in config.items()
            if k not in ("password", "api_key", "token")  # Exclude secrets from key
        )
        return f"{provider_type.value}:{hash(tuple(config_items))}"

    def _is_connection_valid(self, conn: PooledConnection) -> bool:
        """Check if a pooled connection is still valid."""
        now = time.time()

        # Check max age
        if now - conn.created_at > self.max_connection_age:
            logger.debug("Connection exceeded max age, recycling")
            return False

        # Check idle time
        if now - conn.last_used > self.max_idle_time:
            logger.debug("Connection exceeded max idle time, recycling")
            return False

        # Health check
        try:
            if conn.provider.health_check():
                return True
            logger.warning("Connection health check failed")
            return False
        except Exception as e:
            logger.warning(f"Connection health check error: {e}")
            return False

    def _create_connection(self, provider_type: VectorDBProviderEnum, config: dict[str, Any]) -> PooledConnection:
        """Create a new pooled connection."""
        from src.services.knowledge_base.providers.vector_db_factory import VectorDBProviderFactory

        provider = VectorDBProviderFactory.create(provider_type, config)
        provider.connect()

        return PooledConnection(provider=provider)

    @contextmanager
    def get_connection(self, provider_type: VectorDBProviderEnum, config: dict[str, Any]):
        """
        Get a connection from the pool.

        Usage:
            with pool.get_connection(provider_type, config) as conn:
                results = conn.search(...)

        Args:
            provider_type: Type of vector DB provider
            config: Provider configuration

        Yields:
            Vector DB provider instance

        Raises:
            CircuitOpenError: If circuit breaker is open (service unavailable)
        """
        config_key = self._get_config_key(provider_type, config)
        pool = self._pools[config_key]
        conn: PooledConnection | None = None
        circuit_breaker = self._get_circuit_breaker(config_key)

        # Check circuit breaker before attempting connection
        if not circuit_breaker.allow_request():
            with self._lock:
                self._stats[config_key].errors += 1
            raise CircuitOpenError(
                circuit_name=f"vectordb:{provider_type.value}",
                retry_after=circuit_breaker.get_retry_after(),
            )

        with self._lock:
            self._stats[config_key].total_requests += 1

        try:
            # Try to get an existing connection from the pool
            while True:
                try:
                    conn = pool.get_nowait()

                    if self._is_connection_valid(conn):
                        with self._lock:
                            self._stats[config_key].cache_hits += 1
                            self._active[config_key] += 1
                        conn.mark_used()
                        logger.debug(f"Reusing pooled connection for {config_key}")
                        break
                    else:
                        # Connection invalid, close and try again
                        try:
                            conn.provider.disconnect()
                        except Exception:
                            pass
                        conn = None

                except Empty:
                    # No connection available, create new one
                    with self._lock:
                        self._stats[config_key].cache_misses += 1
                        self._stats[config_key].total_connections += 1
                        self._active[config_key] += 1

                    conn = self._create_connection(provider_type, config)
                    logger.debug(f"Created new connection for {config_key}")
                    break

            yield conn.provider

            # Record success for circuit breaker
            circuit_breaker.record_success()

        except CircuitOpenError:
            # Re-raise circuit open errors without recording failure
            raise

        except Exception as e:
            with self._lock:
                self._stats[config_key].errors += 1

            # Record failure for circuit breaker
            circuit_breaker.record_failure()
            logger.error(f"Error using pooled connection: {e}")

            # Don't return broken connection to pool
            if conn:
                try:
                    conn.provider.disconnect()
                except Exception:
                    pass
                conn = None
            raise

        finally:
            with self._lock:
                self._active[config_key] = max(0, self._active[config_key] - 1)

            # Return connection to pool if still valid
            if conn is not None:
                try:
                    if not pool.full():
                        pool.put_nowait(conn)
                        logger.debug(f"Returned connection to pool for {config_key}")
                    else:
                        # Pool full, close connection
                        conn.provider.disconnect()
                        logger.debug(f"Pool full, closed connection for {config_key}")
                except Exception as e:
                    logger.warning(f"Error returning connection to pool: {e}")
                    try:
                        conn.provider.disconnect()
                    except Exception:
                        pass

    def get_stats(self, config_key: str | None = None) -> dict[str, PoolStats]:
        """
        Get pool statistics.

        Args:
            config_key: Optional specific config key, or None for all

        Returns:
            Dictionary of pool statistics
        """
        with self._lock:
            if config_key:
                return {config_key: self._stats.get(config_key, PoolStats())}
            return dict(self._stats)

    def get_circuit_breaker_stats(self, config_key: str | None = None) -> dict[str, dict]:
        """
        Get circuit breaker statistics for monitoring.

        Args:
            config_key: Optional specific config key, or None for all

        Returns:
            Dictionary of circuit breaker states
        """
        with self._lock:
            if config_key:
                cb = self._circuit_breakers.get(config_key)
                return {config_key: cb.get_stats() if cb else {"state": "none"}}
            return {key: cb.get_stats() for key, cb in self._circuit_breakers.items()}

    def clear_pool(self, config_key: str | None = None):
        """
        Clear connections from the pool.

        Args:
            config_key: Optional specific config to clear, or None for all
        """
        keys_to_clear = [config_key] if config_key else list(self._pools.keys())

        for key in keys_to_clear:
            pool = self._pools.get(key)
            if pool:
                while not pool.empty():
                    try:
                        conn = pool.get_nowait()
                        conn.provider.disconnect()
                    except Exception as e:
                        logger.warning(f"Error closing pooled connection: {e}")

                logger.info(f"Cleared connection pool for {key}")

    def close(self):
        """Close all connections and clean up."""
        logger.info("Closing vector DB connection pool")
        self.clear_pool()


# Global pool instance
_vector_db_pool: VectorDBConnectionPool | None = None
_pool_lock = threading.Lock()


def get_vector_db_pool() -> VectorDBConnectionPool:
    """
    Get the global vector DB connection pool.

    Returns:
        VectorDBConnectionPool instance
    """
    global _vector_db_pool

    if _vector_db_pool is None:
        with _pool_lock:
            if _vector_db_pool is None:
                _vector_db_pool = VectorDBConnectionPool()

    return _vector_db_pool


def close_vector_db_pool():
    """Close the global vector DB connection pool."""
    global _vector_db_pool

    with _pool_lock:
        if _vector_db_pool:
            _vector_db_pool.close()
            _vector_db_pool = None
