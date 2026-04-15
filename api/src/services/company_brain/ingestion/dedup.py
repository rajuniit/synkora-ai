"""
Deduplication layer for Company Brain ingestion.

Before a document is queued for embedding we check whether we have already
indexed it.  The dedup key is (tenant_id, source_type, external_id).

Two backends (configured via COMPANY_BRAIN_DEDUP_BACKEND):

  redis_set  — O(1) SISMEMBER check; TTL = COMPANY_BRAIN_DEDUP_TTL_DAYS days.
               A separate Redis SET per (tenant, source_type) stores seen
               external_ids.  Automatically expires so storage stays bounded.

  postgres   — Checks data_source_documents for an existing row with the same
               (tenant_id, data_source.type, external_id).  Always consistent,
               slightly slower (~1ms), but zero extra memory usage.
"""

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _dedup_key(tenant_id: str, source_type: str) -> str:
    """Redis SET key scoped to one tenant + source."""
    safe_tid = str(tenant_id).replace("-", "")
    return f"cb_dedup:{safe_tid}:{source_type}"


def _hash_external_id(external_id: str) -> str:
    """Hash long external IDs to keep Redis SET members small."""
    if len(external_id) <= 64:
        return external_id
    return hashlib.sha256(external_id.encode()).hexdigest()


class RedisSetDedup:
    """
    Dedup using a Redis SET per (tenant, source_type).

    Each SET member is the external_id (or its SHA-256 hash).
    The SET itself has a TTL refreshed on every write — once no new docs
    arrive for COMPANY_BRAIN_DEDUP_TTL_DAYS days the key expires automatically.
    """

    def __init__(self, ttl_days: int = 7):
        self._ttl_seconds = ttl_days * 86_400

    def _get_redis(self) -> Any:
        from src.config.redis import get_redis
        return get_redis()

    async def _get_async_redis(self) -> Any:
        from src.config.redis import get_redis_async
        return get_redis_async()

    async def is_seen(self, tenant_id: str, source_type: str, external_id: str) -> bool:
        """Return True if this document was already indexed."""
        r = await self._get_async_redis()
        key = _dedup_key(tenant_id, source_type)
        member = _hash_external_id(external_id)
        return bool(await r.sismember(key, member))

    async def mark_seen(self, tenant_id: str, source_type: str, external_id: str) -> None:
        """Record that this document has been indexed."""
        r = await self._get_async_redis()
        key = _dedup_key(tenant_id, source_type)
        member = _hash_external_id(external_id)
        pipe = r.pipeline()
        pipe.sadd(key, member)
        pipe.expire(key, self._ttl_seconds)
        await pipe.execute()

    async def mark_seen_batch(
        self, tenant_id: str, source_type: str, external_ids: list[str]
    ) -> None:
        """Batch version of mark_seen — uses a single pipeline."""
        if not external_ids:
            return
        r = await self._get_async_redis()
        key = _dedup_key(tenant_id, source_type)
        members = [_hash_external_id(eid) for eid in external_ids]
        pipe = r.pipeline()
        pipe.sadd(key, *members)
        pipe.expire(key, self._ttl_seconds)
        await pipe.execute()

    async def filter_unseen(
        self, tenant_id: str, source_type: str, external_ids: list[str]
    ) -> list[str]:
        """Return only the external_ids not yet seen (batch check)."""
        if not external_ids:
            return []
        r = await self._get_async_redis()
        key = _dedup_key(tenant_id, source_type)
        members = [_hash_external_id(eid) for eid in external_ids]

        pipe = r.pipeline()
        for m in members:
            pipe.sismember(key, m)
        results = await pipe.execute()

        return [eid for eid, seen in zip(external_ids, results) if not seen]


class PostgresDedup:
    """
    Dedup using the data_source_documents table.

    Checks for existing rows with the same (tenant_id, external_id) within the
    same data source type.  Always consistent with the actual indexed state.
    """

    async def filter_unseen(
        self, tenant_id: str, source_type: str, external_ids: list[str]
    ) -> list[str]:
        if not external_ids:
            return []
        try:
            import asyncpg
            from src.config.settings import get_settings
            settings = get_settings()
            conn = await asyncpg.connect(settings.database_url)
            try:
                rows = await conn.fetch(
                    """
                    SELECT dsd.external_id
                    FROM data_source_documents dsd
                    JOIN data_sources ds ON ds.id = dsd.data_source_id
                    WHERE dsd.tenant_id = $1
                      AND ds.type = $2
                      AND dsd.external_id = ANY($3::text[])
                    """,
                    tenant_id,
                    source_type.upper(),
                    external_ids,
                )
            finally:
                await conn.close()
            seen = {r["external_id"] for r in rows}
            return [eid for eid in external_ids if eid not in seen]
        except Exception as exc:
            logger.error("PostgresDedup.filter_unseen failed: %s", exc)
            return external_ids  # fail open — let the indexer handle duplicates via upsert

    async def is_seen(self, tenant_id: str, source_type: str, external_id: str) -> bool:
        unseen = await self.filter_unseen(tenant_id, source_type, [external_id])
        return external_id not in unseen

    async def mark_seen(self, tenant_id: str, source_type: str, external_id: str) -> None:
        pass  # PG dedup reads from the actual table; no separate state to update

    async def mark_seen_batch(
        self, tenant_id: str, source_type: str, external_ids: list[str]
    ) -> None:
        pass


def get_dedup_backend(backend_type: str | None = None) -> RedisSetDedup | PostgresDedup:
    """
    Return the configured dedup backend.

    Resolution order:
      1. explicit backend_type argument
      2. COMPANY_BRAIN_DEDUP_BACKEND env var
      3. default: redis_set
    """
    from src.config.settings import get_settings
    settings = get_settings()
    resolved = backend_type or getattr(settings, "company_brain_dedup_backend", "redis_set")
    ttl_days = getattr(settings, "company_brain_dedup_ttl_days", 7)

    if resolved == "postgres":
        return PostgresDedup()
    return RedisSetDedup(ttl_days=ttl_days)
