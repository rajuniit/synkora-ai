"""
Prometheus metrics collection and exposure.

Uses the standard prometheus_client library for thread-safe, Prometheus-compatible
metrics. Provides a backward-compatible MetricsCollector wrapper so existing
callers (decorators, app.py endpoints) need no changes.

Metrics exposed:
- HTTP request counts and latencies
- Database connection pool stats
- Cache hit/miss rates
- LLM API latencies and token counts
- Circuit breaker states
- Rate limiter events
"""

import logging
import re
import threading
import time
from functools import wraps
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Isolated registry — avoids conflicts with other libraries that use the default registry.
_registry = CollectorRegistry()

# ---------------------------------------------------------------------------
# Metric definitions (instantiated once at module load, thread-safe by design)
# ---------------------------------------------------------------------------

# Labeled HTTP metrics — sliceable by method, endpoint, and status_code.
# These are populated by PrometheusMiddleware, not by the track_request_duration decorator.
_HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
    registry=_registry,
)
_HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=_registry,
)

# Regex for path normalization — collapses high-cardinality path segments (UUIDs,
# numeric IDs) into placeholders so Prometheus label cardinality stays bounded.
_UUID_RE = re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_NUM_ID_RE = re.compile(r"/\d+")


def _normalize_path(path: str) -> str:
    """Replace UUID and numeric path segments with placeholders."""
    path = _UUID_RE.sub("/{uuid}", path)
    path = _NUM_ID_RE.sub("/{id}", path)
    return path


_DB_POOL_SIZE = Gauge("db_pool_size", "Database connection pool size", registry=_registry)
_DB_POOL_CHECKED_OUT = Gauge(
    "db_pool_checked_out", "Database connections currently in use", registry=_registry
)
_DB_QUERIES = Counter("db_queries_total", "Total database queries", registry=_registry)
_CACHE_HITS = Counter("cache_hits_total", "Total cache hits", registry=_registry)
_CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", registry=_registry)
_LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    labelnames=["provider", "model"],
    registry=_registry,
)
_LLM_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM API request duration in seconds",
    labelnames=["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=_registry,
)
_LLM_TOKENS = Counter("llm_tokens_total", "Total LLM tokens processed", registry=_registry)
_CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    registry=_registry,
)
_RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit exceeded events",
    registry=_registry,
)

# Map metric names to their prometheus_client objects for generic access.
# NOTE: _HTTP_REQUESTS and _HTTP_DURATION are labeled and tracked by
# PrometheusMiddleware — they are intentionally excluded from these dicts
# so that unlabeled inc_counter/observe_histogram calls don't fail.
_COUNTERS: dict[str, Counter] = {
    "db_queries_total": _DB_QUERIES,
    "cache_hits_total": _CACHE_HITS,
    "cache_misses_total": _CACHE_MISSES,
    # NOTE: llm_requests_total and llm_request_duration_seconds are labeled metrics
    # (provider, model) — they are NOT in these dicts because calling .inc()/.observe()
    # without labels raises an error. Access them only via track_llm_request decorator.
    "llm_tokens_total": _LLM_TOKENS,
    "rate_limit_exceeded_total": _RATE_LIMIT_EXCEEDED,
}
_GAUGES: dict[str, Gauge] = {
    "db_pool_size": _DB_POOL_SIZE,
    "db_pool_checked_out": _DB_POOL_CHECKED_OUT,
    "circuit_breaker_state": _CIRCUIT_BREAKER_STATE,
}
_HISTOGRAMS: dict[str, Histogram] = {
    # llm_request_duration_seconds excluded — it is labeled (provider, model)
}


class MetricsCollector:
    """
    Backward-compatible wrapper around prometheus_client metrics.

    Keeps the same interface as the previous custom implementation so existing
    callers (app.py, decorators) require no changes. All operations are
    thread-safe via prometheus_client's internal locks.
    """

    def __init__(self) -> None:
        logger.info("Metrics collector initialized (prometheus_client backend)")

    # ------------------------------------------------------------------
    # Registration helpers — no-ops when the metric already exists
    # ------------------------------------------------------------------

    def register_counter(self, name: str, description: str) -> Counter:  # noqa: ARG002
        return _COUNTERS.get(name, _DB_QUERIES)

    def register_gauge(self, name: str, description: str) -> Gauge:  # noqa: ARG002
        return _GAUGES.get(name, _DB_POOL_SIZE)

    def register_histogram(
        self,
        name: str,
        description: str,  # noqa: ARG002
        buckets: list[float] | None = None,  # noqa: ARG002
    ) -> Histogram:
        return _HISTOGRAMS.get(name, _LLM_DURATION)

    # ------------------------------------------------------------------
    # Value operations — delegate to prometheus_client (thread-safe)
    # ------------------------------------------------------------------

    def inc_counter(self, name: str, amount: float = 1, labels: dict[str, str] | None = None) -> None:  # noqa: ARG002
        metric = _COUNTERS.get(name)
        if metric is not None:
            metric.inc(amount)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:  # noqa: ARG002
        metric = _GAUGES.get(name)
        if metric is not None:
            metric.set(value)

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:  # noqa: ARG002
        metric = _HISTOGRAMS.get(name)
        if metric is not None:
            metric.observe(value)

    def get_metric(self, name: str) -> Any | None:
        return _COUNTERS.get(name) or _GAUGES.get(name) or _HISTOGRAMS.get(name)

    def collect_all(self) -> dict[str, Any]:
        """
        Return a summary of all metrics (for the /api/v1/stats/performance endpoint).

        Uses the public CollectorRegistry.collect() API instead of private attributes
        so this remains stable across prometheus_client version upgrades.
        For labeled metrics (e.g. LLM by provider/model, HTTP by endpoint), values are
        summed across all label combinations to produce a single aggregate figure.
        """
        result: dict[str, Any] = {}
        for metric_family in _registry.collect():
            name = metric_family.name
            mtype = metric_family.type
            # Exclude _created timestamp samples emitted by Counters in prometheus_client ≥0.12
            value_samples = [s for s in metric_family.samples if not s.name.endswith("_created")]
            if mtype == "counter":
                result[name] = {"type": "counter", "value": sum(s.value for s in value_samples)}
            elif mtype == "gauge":
                result[name] = {"type": "gauge", "value": sum(s.value for s in value_samples)}
            elif mtype == "histogram":
                count = sum(s.value for s in value_samples if s.name.endswith("_count"))
                total = sum(s.value for s in value_samples if s.name.endswith("_sum"))
                result[name] = {"type": "histogram", "count": count, "sum": total}
        return result

    def to_prometheus_format(self) -> str:
        """Export metrics in standard Prometheus text format."""
        return generate_latest(_registry).decode("utf-8")


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_metrics_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector (lazy singleton)."""
    global _metrics_collector
    if _metrics_collector is None:
        with _collector_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    return _metrics_collector


# ---------------------------------------------------------------------------
# Prometheus ASGI middleware — labeled HTTP metrics
# ---------------------------------------------------------------------------


class PrometheusMiddleware:
    """
    Pure ASGI middleware that records per-request HTTP metrics with proper labels.

    Labels: method (GET/POST/…), endpoint (path with UUIDs/IDs normalized),
    status_code (response HTTP status as a string).

    Prometheus best practice is to use labels so alert rules can filter by
    endpoint and method. Without labels a single counter is nearly useless
    for production alerting.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "unknown")
        path = scope.get("path", "unknown")
        endpoint = _normalize_path(path)

        start = time.time()
        status_code = "500"

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start
            labels = {"method": method, "endpoint": endpoint, "status_code": status_code}
            _HTTP_REQUESTS.labels(**labels).inc()
            _HTTP_DURATION.labels(**labels).observe(duration)


# ---------------------------------------------------------------------------
# Decorators (unchanged public API)
# ---------------------------------------------------------------------------


def track_request_duration(func):
    """
    Decorator to time a route handler for observability purposes.

    NOTE: HTTP request counting and duration recording are now handled by
    PrometheusMiddleware (with proper method/endpoint/status_code labels).
    This decorator retains its public API for callers but no longer records
    metrics itself to avoid double-counting.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    import asyncio

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def track_llm_request(provider: str, model: str):
    """Decorator to track LLM request metrics labeled by provider and model."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            _LLM_REQUESTS.labels(provider=provider, model=model).inc()
            try:
                return await func(*args, **kwargs)
            finally:
                _LLM_DURATION.labels(provider=provider, model=model).observe(time.time() - start)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            _LLM_REQUESTS.labels(provider=provider, model=model).inc()
            try:
                return func(*args, **kwargs)
            finally:
                _LLM_DURATION.labels(provider=provider, model=model).observe(time.time() - start)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
