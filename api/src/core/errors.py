"""
Custom error classes and error handling.

Provides structured error responses and custom exceptions.
"""

from typing import Any


class APIError(Exception):
    """Base API error class."""

    code = 500
    message = "Internal server error"
    error_code = "internal_error"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        error_dict = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status": self.code,
            }
        }
        if self.details:
            error_dict["error"]["details"] = self.details
        return error_dict


class BadRequestError(APIError):
    """400 Bad Request."""

    code = 400
    message = "Bad request"
    error_code = "bad_request"


class UnauthorizedError(APIError):
    """401 Unauthorized."""

    code = 401
    message = "Unauthorized"
    error_code = "unauthorized"


class ForbiddenError(APIError):
    """403 Forbidden."""

    code = 403
    message = "Forbidden"
    error_code = "forbidden"


class PermissionDeniedError(ForbiddenError):
    """Permission denied error."""

    message = "Permission denied"
    error_code = "permission_denied"


class NotFoundError(APIError):
    """404 Not Found."""

    code = 404
    message = "Resource not found"
    error_code = "not_found"


class ConflictError(APIError):
    """409 Conflict."""

    code = 409
    message = "Resource conflict"
    error_code = "conflict"


class ValidationError(BadRequestError):
    """Validation error."""

    message = "Validation failed"
    error_code = "validation_error"


class RateLimitError(APIError):
    """429 Too Many Requests."""

    code = 429
    message = "Rate limit exceeded"
    error_code = "rate_limit_exceeded"


class ServiceUnavailableError(APIError):
    """503 Service Unavailable."""

    code = 503
    message = "Service temporarily unavailable"
    error_code = "service_unavailable"


def safe_error_message(
    error: Exception, default_message: str = "An unexpected error occurred", include_type: bool = False
) -> str:
    """
    Generate a safe error message that doesn't expose sensitive details.

    In production, this returns a generic message. In development,
    it can optionally include the exception type for debugging.

    Args:
        error: The exception that was raised
        default_message: Message to show to users
        include_type: Whether to include exception type (for development)

    Returns:
        Safe error message string

    Security:
        - Never exposes stack traces
        - Never exposes internal paths
        - Never exposes database details
        - Never exposes configuration details
    """
    import os

    is_development = os.getenv("APP_ENV", "development") == "development"

    if is_development and include_type:
        # In development, include exception type for easier debugging
        error_type = type(error).__name__
        return f"{default_message} ({error_type})"

    # In production (or if include_type is False), return only the default message
    return default_message
