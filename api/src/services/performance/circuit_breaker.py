"""
Circuit breaker pattern for external services.

Prevents cascading failures by temporarily stopping requests to
failing services and allowing them time to recover.
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker '{circuit_name}' is open. Retry after {retry_after:.1f} seconds.")


class CircuitBreaker:
    """
    Circuit breaker for protecting external service calls.

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service recovered

    Transitions:
    - CLOSED -> OPEN: When failure threshold is reached
    - OPEN -> HALF_OPEN: After recovery timeout
    - HALF_OPEN -> CLOSED: On successful request
    - HALF_OPEN -> OPEN: On failed request
    """

    DEFAULT_FAILURE_THRESHOLD = 5
    DEFAULT_RECOVERY_TIMEOUT = 30  # seconds
    DEFAULT_HALF_OPEN_MAX_REQUESTS = 3

    def __init__(
        self,
        name: str,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: int = DEFAULT_RECOVERY_TIMEOUT,
        half_open_max_requests: int = DEFAULT_HALF_OPEN_MAX_REQUESTS,
        excluded_exceptions: tuple | None = None,
    ):
        """
        Initialize the circuit breaker.

        Args:
            name: Name of the circuit (for logging/monitoring)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_requests: Max requests allowed in half-open state
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self.excluded_exceptions = excluded_exceptions or ()

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = threading.RLock()
        self._last_state_change = time.time()
        self._half_open_requests = 0

        logger.info(
            f"Circuit breaker '{name}' initialized: threshold={failure_threshold}, recovery={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state

    def _check_state_transition(self):
        """Check if state should transition based on timeouts."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_state_change >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_requests = 0

        logger.info(f"Circuit breaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}")

    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_requests += 1
                if self._half_open_requests >= self.half_open_max_requests:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, exception: Exception):
        """Record a failed request."""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed through."""
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                self._stats.rejected_requests += 1
                return False
            else:  # HALF_OPEN
                return self._half_open_requests < self.half_open_max_requests

    # Public API for manual integration (used by connection pools, etc.)
    def record_success(self):
        """Record a successful request (public API)."""
        self._record_success()

    def record_failure(self, exception: Exception | None = None):
        """Record a failed request (public API)."""
        self._record_failure(exception or Exception("Unknown failure"))

    def allow_request(self) -> bool:
        """Check if request should be allowed (public API)."""
        return self._should_allow_request()

    def get_retry_after(self) -> float:
        """Get seconds until circuit might allow requests again."""
        if self._state != CircuitState.OPEN:
            return 0
        return max(0, self.recovery_timeout - (time.time() - self._last_state_change))

    def call(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from the function
        """
        if not self._should_allow_request():
            retry_after = self.recovery_timeout - (time.time() - self._last_state_change)
            raise CircuitBreakerOpen(self.name, max(0, retry_after))

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            if isinstance(e, self.excluded_exceptions):
                # Don't count as failure
                self._record_success()
            else:
                self._record_failure(e)
            raise

    async def call_async(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """
        Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from the function
        """
        if not self._should_allow_request():
            retry_after = self.recovery_timeout - (time.time() - self._last_state_change)
            raise CircuitBreakerOpen(self.name, max(0, retry_after))

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            if isinstance(e, self.excluded_exceptions):
                self._record_success()
            else:
                self._record_failure(e)
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "rejected_requests": self._stats.rejected_requests,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_failure_time": self._stats.last_failure_time,
                "last_success_time": self._stats.last_success_time,
            }

    def reset(self):
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._last_state_change = time.time()
            self._half_open_requests = 0
            logger.info(f"Circuit breaker '{self.name}' reset")


def circuit_breaker(
    name: str,
    failure_threshold: int = CircuitBreaker.DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout: int = CircuitBreaker.DEFAULT_RECOVERY_TIMEOUT,
    excluded_exceptions: tuple | None = None,
):
    """
    Decorator to wrap a function with circuit breaker protection.

    Usage:
        @circuit_breaker("external_api")
        async def call_external_api():
            ...

    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before recovery attempt
        excluded_exceptions: Exceptions that don't count as failures
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        excluded_exceptions=excluded_exceptions,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return breaker.call(func, *args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            async_wrapper._circuit_breaker = breaker
            return async_wrapper
        else:
            sync_wrapper._circuit_breaker = breaker
            return sync_wrapper

    return decorator


# Global circuit breakers registry
_circuit_breakers: dict[str, CircuitBreaker] = {}
_cb_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = CircuitBreaker.DEFAULT_FAILURE_THRESHOLD,
    recovery_timeout: int = CircuitBreaker.DEFAULT_RECOVERY_TIMEOUT,
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.

    Args:
        name: Circuit breaker name
        failure_threshold: Failure threshold (only used on creation)
        recovery_timeout: Recovery timeout (only used on creation)

    Returns:
        CircuitBreaker instance
    """
    global _circuit_breakers

    if name not in _circuit_breakers:
        with _cb_lock:
            if name not in _circuit_breakers:
                _circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                )

    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}
