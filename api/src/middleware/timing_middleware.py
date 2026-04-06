"""
Request Timing Middleware — data-driven latency diagnostics.

Instruments the full request pipeline and emits:
  - `Server-Timing` response header with per-component breakdown
  - `X-Request-ID` response header for log correlation
  - Structured WARNING log for every request exceeding SLOW_THRESHOLD_MS

Usage in browser DevTools:
  Network tab → select a request → Timing tab → "Server Timing" section.

Log format (WARNING level, one line per slow request):
  SLOW_REQUEST rid=abc123 GET /api/v1/agents total=312.4ms status=200 |
    rate_limit=1.2ms plan_restriction=45.3ms db_queries=38.1ms(7) auth=9.4ms handler=210.0ms

Inner middlewares write their self-time into scope["state"]["_timing"]:
    state = scope.get("state") or {}
    timing = state.get("_timing")
    if timing is not None:
        timing["my_component"] = (time.perf_counter() - t0) * 1000

DB query timing is injected via SQLAlchemy engine events in core/database.py
(no per-query code change needed).
"""

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Log a warning for any request that takes longer than this.
SLOW_THRESHOLD_MS: float = 200.0


class RequestTimingMiddleware:
    """
    Pure ASGI outermost timing middleware.

    Must be the LAST middleware registered in app.py (i.e. added last via
    app.add_middleware) so it becomes the outermost layer that wraps everything.

    Lifecycle:
      1. Creates timing state in scope before any inner middleware runs.
      2. After the full response is sent, reads the timing state assembled by
         inner middlewares and emits Server-Timing + logs.
    """

    def __init__(self, app: ASGIApp, slow_threshold_ms: float = SLOW_THRESHOLD_MS) -> None:
        self.app = app
        self.slow_threshold_ms = slow_threshold_ms

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Initialise timing context.  Inner middlewares will write into _timing.
        if "state" not in scope:
            scope["state"] = {}

        request_id = uuid.uuid4().hex[:8]
        scope["state"]["_request_id"] = request_id
        scope["state"]["_timing"] = {}          # {component: ms}
        scope["state"]["_timing_start"] = time.perf_counter()

        method = scope.get("method", "?")
        path = scope.get("path", "?")
        status_code = "???"

        async def send_with_timing(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 0))
                total_ms = (time.perf_counter() - scope["state"]["_timing_start"]) * 1000
                timing: dict = scope["state"].get("_timing", {})

                # ---- Server-Timing header --------------------------------
                # Format: "total;dur=312.4, rate_limit;dur=1.2, ..."
                parts = [f"total;dur={total_ms:.1f}"]
                for name, val in timing.items():
                    if isinstance(val, (int, float)):
                        parts.append(f"{name};dur={val:.1f}")
                server_timing_value = ", ".join(parts)

                # ---- Slow-request structured log -------------------------
                if total_ms >= self.slow_threshold_ms:
                    detail_parts = " ".join(
                        f"{k}={v:.1f}ms" if isinstance(v, float) else f"{k}={v}"
                        for k, v in timing.items()
                    )
                    logger.warning(
                        "SLOW_REQUEST rid=%s %s %s total=%.1fms status=%s | %s",
                        request_id,
                        method,
                        path,
                        total_ms,
                        status_code,
                        detail_parts or "(no breakdown available)",
                    )
                else:
                    logger.debug(
                        "REQUEST rid=%s %s %s total=%.1fms status=%s",
                        request_id,
                        method,
                        path,
                        total_ms,
                        status_code,
                    )

                # ---- Inject headers --------------------------------------
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.append((b"server-timing", server_timing_value.encode()))
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_timing)
