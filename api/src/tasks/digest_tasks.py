"""
Celery tasks for nightly daily digest generation across all data sources.

Beat schedule (defined in celery_app.py):
  - generate_all_daily_digests: runs at 11 PM UTC every day
  - Individual per-source tasks are dispatched by the coordinator.
"""

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.generate_all_daily_digests", bind=True, max_retries=1)
def generate_all_daily_digests(self, target_date_iso: str | None = None) -> dict[str, Any]:
    """
    Coordinator task: dispatches per-source digest tasks for all active data sources.

    Args:
        target_date_iso: ISO date string (YYYY-MM-DD) to generate digests for.
                         Defaults to yesterday (UTC).
    """
    if target_date_iso:
        target_date = date.fromisoformat(target_date_iso)
    else:
        target_date = (datetime.now(UTC) - timedelta(days=1)).date()

    logger.info(f"Dispatching daily digest generation for {target_date.isoformat()}")
    return asyncio.run(_dispatch_digest_tasks(target_date))


@celery_app.task(name="tasks.generate_data_source_digest", bind=True, max_retries=2, default_retry_delay=300)
def generate_data_source_digest(self, data_source_id: str, target_date_iso: str) -> dict[str, Any]:
    """
    Generate the daily digest for a single data source.

    Args:
        data_source_id: Integer ID of the DataSource (passed as string for Celery serialization).
        target_date_iso: ISO date string (YYYY-MM-DD).
    """
    target_date = date.fromisoformat(target_date_iso)
    ds_id = int(data_source_id)

    logger.info(f"Generating digest for data source {data_source_id} on {target_date_iso}")

    try:
        result = asyncio.run(_generate_single_digest(ds_id, target_date))
        return result
    except Exception as exc:
        logger.error(f"Digest generation failed for {data_source_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300 * (2**self.request.retries))


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _dispatch_digest_tasks(target_date: date) -> dict[str, Any]:
    from sqlalchemy import select

    from src.core.database import create_celery_async_session
    from src.models.data_source import DataSource, DataSourceStatus
    from src.services.data_sources.digest.registry import supported_source_types

    supported = set(supported_source_types())

    async with create_celery_async_session()() as db:
        result = await db.execute(
            select(DataSource).where(DataSource.status == DataSourceStatus.ACTIVE)
        )
        data_sources = result.scalars().all()

    queued = 0
    skipped = 0

    for ds in data_sources:
        source_type = str(ds.type).upper().replace("DATASOURCETYPE.", "")
        if source_type not in supported:
            skipped += 1
            continue

        generate_data_source_digest.delay(
            data_source_id=str(ds.id),
            target_date_iso=target_date.isoformat(),
        )
        queued += 1

    logger.info(f"Dispatched {queued} digest tasks for {target_date.isoformat()} ({skipped} skipped — no extractor)")
    return {"target_date": target_date.isoformat(), "queued": queued, "skipped": skipped}


async def _generate_single_digest(data_source_id: int, target_date: date) -> dict[str, Any]:
    from src.core.database import create_celery_async_session
    from src.services.data_sources.digest.service import DigestService

    async with create_celery_async_session()() as db:
        service = DigestService(db)
        digest = await service.generate(data_source_id, target_date)

    return {
        "data_source_id": str(data_source_id),
        "target_date": target_date.isoformat(),
        "status": digest.status,
        "items_processed": digest.items_processed,
        "error": digest.error,
    }
