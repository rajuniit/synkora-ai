"""
Search backend factory.

Resolution order for the backend type:
  1. Explicit `backend_type` argument to get_search_backend()
  2. COMPANY_BRAIN_SEARCH_BACKEND environment variable
  3. Default: qdrant_hybrid

Usage:
    from src.services.company_brain.search.factory import get_search_backend

    backend = get_search_backend()
    results = await backend.search(tenant_id=..., query=...)
"""

import logging
from typing import Any

from .base import BaseSearchBackend, SearchBackendType

logger = logging.getLogger(__name__)

# Module-level cache — one backend instance per (type, frozen config hash)
_cache: dict[str, BaseSearchBackend] = {}


def get_search_backend(
    backend_type: str | None = None,
    config_override: dict[str, Any] | None = None,
) -> BaseSearchBackend:
    """
    Return the configured search backend (cached singleton per process).

    Args:
        backend_type:    Override the backend type. If None, reads from settings.
        config_override: Optional dict passed to the backend constructor.
                         Useful for per-tenant custom ES endpoints etc.

    Returns:
        An initialised BaseSearchBackend implementation.
    """
    from src.config.settings import get_settings

    settings = get_settings()
    resolved_type = backend_type or getattr(settings, "company_brain_search_backend", "qdrant_hybrid")
    cache_key = f"{resolved_type}:{_stable_hash(config_override)}"

    if cache_key not in _cache:
        _cache[cache_key] = _build_backend(resolved_type, config_override or {})
        logger.info("Initialised Company Brain search backend: %s", resolved_type)

    return _cache[cache_key]


def _build_backend(backend_type: str, config: dict[str, Any]) -> BaseSearchBackend:
    try:
        bt = SearchBackendType(backend_type)
    except ValueError:
        raise ValueError(
            f"Unknown Company Brain search backend: '{backend_type}'. "
            f"Valid options: {[e.value for e in SearchBackendType]}"
        )

    match bt:
        case SearchBackendType.QDRANT_HYBRID:
            from .qdrant_hybrid_backend import QdrantHybridBackend

            return QdrantHybridBackend(config)

        case SearchBackendType.POSTGRES_FTS:
            from .postgres_fts_backend import PostgresFTSBackend

            return PostgresFTSBackend(config)

        case SearchBackendType.ELASTICSEARCH:
            from .elasticsearch_backend import ElasticsearchBackend

            return ElasticsearchBackend(config)

        case SearchBackendType.TYPESENSE:
            raise NotImplementedError("Typesense backend is planned but not yet implemented.")


def _stable_hash(obj: Any) -> str:
    """Deterministic hash for use as a cache key (not cryptographic)."""
    import hashlib
    import json

    try:
        return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:8]
    except Exception:
        return "default"


def invalidate_cache() -> None:
    """Clear the backend cache. Useful in tests or after config changes."""
    _cache.clear()
