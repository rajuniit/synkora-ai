"""
Performance optimization services.

This module contains services for improving application performance:
- Connection pooling for vector databases
- LLM client pooling
- Circuit breakers for external services
- Rate limiting
"""

from .circuit_breaker import CircuitBreaker, CircuitState
from .connection_pool import CircuitOpenError, VectorDBConnectionPool, get_vector_db_pool
from .llm_client_pool import LLMClientPool, get_llm_client_pool
from .rate_limiter import RateLimiter, get_rate_limiter

__all__ = [
    "VectorDBConnectionPool",
    "get_vector_db_pool",
    "CircuitOpenError",
    "LLMClientPool",
    "get_llm_client_pool",
    "CircuitBreaker",
    "CircuitState",
    "RateLimiter",
    "get_rate_limiter",
]
