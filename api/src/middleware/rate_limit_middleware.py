"""
Rate limiting middleware for FastAPI.

Provides request rate limiting with Redis backend for distributed
rate limiting across multiple application instances.

NOTE: Uses pure ASGI pattern instead of BaseHTTPMiddleware to avoid
TaskGroup cancellation issues with async database sessions.
"""

import hashlib
import logging
from collections.abc import Callable

from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.services.performance.rate_limiter import RateLimitResult, get_rate_limiter
from src.utils.ip_utils import get_client_ip

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Pure ASGI Rate limiting middleware for FastAPI.

    Uses pure ASGI pattern to avoid BaseHTTPMiddleware TaskGroup cancellation issues.

    Features:
    - Redis-backed distributed rate limiting
    - Configurable limits per endpoint
    - Multiple key strategies (IP, user, API key)
    - Proper HTTP headers (X-RateLimit-*)
    """

    # Default limits
    DEFAULT_REQUESTS = 100
    DEFAULT_WINDOW = 60  # seconds

    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        # Auth endpoints — strict to limit brute-force and credential stuffing.
        # Account lockout (Redis-based) runs on top of this for additional protection.
        "/console/api/auth/signin": {"requests": 10, "window": 60},
        "/console/api/auth/login": {"requests": 10, "window": 60},
        "/console/api/auth/signup": {"requests": 5, "window": 60},
        "/console/api/auth/register": {"requests": 5, "window": 60},
        "/console/api/auth/forgot-password": {"requests": 5, "window": 60},
        "/console/api/auth/resend-verification": {"requests": 3, "window": 60},
        "/console/api/auth/verify-email": {"requests": 10, "window": 60},
        "/console/api/auth/refresh": {"requests": 20, "window": 60},
        # Chat endpoints - more restrictive
        "/api/v1/agents/": {"requests": 60, "window": 60},
        "/v1/chat/": {"requests": 30, "window": 60},
        # File upload - very restrictive
        "/console/api/files/upload": {"requests": 20, "window": 60},
        "/api/v1/files/upload": {"requests": 20, "window": 60},
        "/api/v1/data-analysis/upload": {"requests": 10, "window": 60},
        # Public webhook endpoints - moderate
        "/webhook/": {"requests": 100, "window": 60},
        # Health check - very permissive
        "/health": {"requests": 1000, "window": 60},
    }

    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = [
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/health",
        "/api/health",
        "/live",
        "/ready",
    ]

    def __init__(
        self,
        app: ASGIApp,
        default_requests: int = DEFAULT_REQUESTS,
        default_window: int = DEFAULT_WINDOW,
        enabled: bool = True,
        key_func: Callable[[StarletteRequest], str] | None = None,
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI application
            default_requests: Default max requests per window
            default_window: Default window size in seconds
            enabled: Whether rate limiting is enabled
            key_func: Optional custom function to extract rate limit key
        """
        self.app = app
        self.default_requests = default_requests
        self.default_window = default_window
        self.enabled = enabled
        self.key_func = key_func or self._default_key_func
        self.rate_limiter = get_rate_limiter()

        logger.info(
            f"Rate limit middleware initialized: enabled={enabled}, default={default_requests} req/{default_window}s"
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip if disabled
        if not self.enabled:
            await self.app(scope, receive, send)
            return

        # Create a request object for header access
        request = StarletteRequest(scope, receive, send)
        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # Skip OPTIONS requests (CORS preflight)
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Skip excluded paths
        if self._should_skip_path(path):
            await self.app(scope, receive, send)
            return

        # Get rate limit key
        key = self.key_func(request)

        # Get limits for this path
        max_requests, window = self._get_limit_for_path(path)

        # Check rate limit (async — does not block the event loop)
        result: RateLimitResult = await self.rate_limiter.check(
            key=f"{key}:{path}",
            max_requests=max_requests,
            window=window,
        )

        if not result.allowed:
            # Rate limited - return 429
            logger.warning(
                f"Rate limit exceeded | key={key} path={path} method={method} "
                f"limit={max_requests}/{window}s retry_after={result.retry_after:.1f}s"
            )

            response = JSONResponse(
                status_code=429,
                content={
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": result.retry_after,
                },
                headers=result.to_headers(),
            )
            await response(scope, receive, send)
            return

        # Downgraded to DEBUG — at production volume this INFO log generated thousands
        # of log lines per minute and added measurable I/O overhead
        if path.startswith("/api/v1/agents/"):
            logger.debug(
                f"Rate limit OK | key={key} path={path} method={method} remaining={result.remaining}/{max_requests}"
            )

        # Add rate limit headers to response
        rate_limit_headers = [
            (header_name.lower().encode(), str(header_value).encode())
            for header_name, header_value in result.to_headers().items()
        ]

        async def send_with_rate_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(rate_limit_headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_rate_headers)

    def _default_key_func(self, request: StarletteRequest) -> str:
        """
        Default function to extract rate limit key from request.

        Priority:
        1. API key from header
        2. User ID from auth
        3. Client IP address

        Args:
            request: Starlette request

        Returns:
            Rate limit key
        """
        # Check for API key — use SHA-256 for a stable, privacy-preserving key.
        # Python's built-in hash() is randomized per process (PYTHONHASHSEED) so
        # it changes on every restart, which would reset per-key Redis counters.
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if api_key and len(api_key) > 10:
            key_hash = hashlib.sha256(api_key.encode(), usedforsecurity=False).hexdigest()[:16]
            return f"apikey:{key_hash}"

        # Check for user ID in state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Check for tenant ID
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fall back to IP address
        direct_ip = request.client.host if request.client else "unknown"
        client_ip = get_client_ip(
            direct_ip=direct_ip,
            forwarded_for=request.headers.get("X-Forwarded-For"),
            real_ip=request.headers.get("X-Real-IP"),
        )
        return f"ip:{client_ip}"

    def _get_limit_for_path(self, path: str) -> tuple[int, int]:
        """
        Get rate limit for a specific path.

        Args:
            path: Request path

        Returns:
            Tuple of (max_requests, window_seconds)
        """
        # Check endpoint-specific limits
        for prefix, limits in self.ENDPOINT_LIMITS.items():
            if path.startswith(prefix):
                return limits["requests"], limits["window"]

        return self.default_requests, self.default_window

    def _should_skip_path(self, path: str) -> bool:
        """Check if path should skip rate limiting."""
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False


def create_rate_limit_middleware(
    enabled: bool = True,
    default_requests: int = RateLimitMiddleware.DEFAULT_REQUESTS,
    default_window: int = RateLimitMiddleware.DEFAULT_WINDOW,
):
    """
    Factory function to create rate limit middleware.

    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            **create_rate_limit_middleware(enabled=True)
        )

    Args:
        enabled: Whether to enable rate limiting
        default_requests: Default max requests per window
        default_window: Default window size in seconds

    Returns:
        Dictionary of middleware kwargs
    """
    return {
        "enabled": enabled,
        "default_requests": default_requests,
        "default_window": default_window,
    }
