"""Core functionality package."""

from .database import (
    Base,
    SessionLocal,
    close_async_db,
    close_db,
    get_async_db,
    get_async_session_factory,
    get_db,
    get_db_context,
    init_db,
)
from .errors import (
    APIError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)

__all__ = [
    # Database (sync)
    "Base",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "close_db",
    # Database (async)
    "get_async_session_factory",
    "get_async_db",
    "close_async_db",
    # Errors
    "APIError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
]
