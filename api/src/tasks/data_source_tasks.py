"""
Celery tasks for data source synchronization operations.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from src.celery_app import celery_app
from src.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    name="sync_data_source_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def sync_data_source_task(
    self, data_source_id: str, full_sync: bool = False, tenant_id: str | None = None
) -> dict[str, Any]:
    """
    Synchronize a data source with external provider.

    Args:
        data_source_id: Data source UUID
        full_sync: Whether to perform full sync or incremental
        tenant_id: Tenant ID (optional)

    Returns:
        dict: Sync results with counts and status
    """
    db = SessionLocal()

    try:
        from src.models.data_source import DataSource

        logger.info(f"🔄 Starting sync for data source {data_source_id}")

        data_source = db.query(DataSource).filter(DataSource.id == uuid.UUID(data_source_id)).first()

        if not data_source:
            logger.error(f"Data source {data_source_id} not found")
            return {"success": False, "error": "Data source not found"}

        # Route to appropriate connector based on type
        if data_source.type == "gmail":
            from src.services.data_sources.gmail_connector import GmailConnector

            connector = GmailConnector(db, data_source)
        elif data_source.type == "slack":
            from src.services.data_sources.slack_connector import SlackConnector

            connector = SlackConnector(db, data_source)
        elif data_source.type == "github":
            from src.services.data_sources.github_connector import GitHubConnector

            connector = GitHubConnector(db, data_source)
        else:
            logger.error(f"Unsupported data source type: {data_source.type}")
            return {"success": False, "error": f"Unsupported type: {data_source.type}"}

        # Perform sync
        result = connector.sync(full_sync=full_sync)

        # Update last sync time
        data_source.last_synced_at = datetime.now(UTC)
        db.commit()

        logger.info(f"✅ Sync completed for data source {data_source_id}: {result}")

        return {"success": True, "data_source_id": data_source_id, "type": data_source.type, **result}

    except Exception as exc:
        logger.error(f"❌ Error syncing data source {data_source_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="sync_all_data_sources_task")
def sync_all_data_sources_task(tenant_id: str | None = None) -> dict[str, Any]:
    """
    Sync all active data sources for a tenant or all tenants.

    Args:
        tenant_id: Optional tenant ID to limit sync scope

    Returns:
        dict: Summary of sync operations
    """
    db = SessionLocal()

    try:
        from src.models.data_source import DataSource

        logger.info("🔄 Starting sync for all data sources")

        query = db.query(DataSource).filter(DataSource.is_active)

        if tenant_id:
            query = query.filter(DataSource.tenant_id == uuid.UUID(tenant_id))

        data_sources = query.all()

        results = {"total": len(data_sources), "queued": 0, "failed": 0, "sources": []}

        for ds in data_sources:
            try:
                # Queue individual sync task
                sync_data_source_task.delay(data_source_id=str(ds.id), full_sync=False)
                results["queued"] += 1
                results["sources"].append({"id": str(ds.id), "type": ds.type, "status": "queued"})
            except Exception as e:
                logger.error(f"Failed to queue sync for {ds.id}: {e}")
                results["failed"] += 1
                results["sources"].append({"id": str(ds.id), "type": ds.type, "status": "failed", "error": str(e)})

        logger.info(f"✅ Queued {results['queued']} data source syncs")

        return results

    except Exception as exc:
        logger.error(f"❌ Error in bulk data source sync: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

    finally:
        db.close()


@celery_app.task(name="process_data_source_document_task", bind=True, max_retries=3)
def process_data_source_document_task(self, document_id: str, data_source_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Process a document from a data source (extract, index, embed).

    Args:
        document_id: Document UUID
        data_source_id: Data source UUID
        tenant_id: Tenant UUID

    Returns:
        dict: Processing results
    """
    db = SessionLocal()

    try:
        from src.services.data_sources.document_processor import DocumentProcessor

        logger.info(f"📄 Processing document {document_id} from data source {data_source_id}")

        processor = DocumentProcessor(db)
        result = processor.process_document(
            document_id=uuid.UUID(document_id), data_source_id=uuid.UUID(data_source_id), tenant_id=uuid.UUID(tenant_id)
        )

        logger.info(f"✅ Document {document_id} processed successfully")

        return result

    except Exception as exc:
        logger.error(f"❌ Error processing document {document_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="cleanup_old_data_source_items_task")
def cleanup_old_data_source_items_task(data_source_id: str, days_old: int = 90) -> dict[str, Any]:
    """
    Clean up old items from a data source.

    Args:
        data_source_id: Data source UUID
        days_old: Delete items older than this many days

    Returns:
        dict: Cleanup results
    """
    db = SessionLocal()

    try:
        from datetime import timedelta

        from src.models.data_source_item import DataSourceItem

        logger.info(f"🧹 Cleaning up items older than {days_old} days from {data_source_id}")

        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        deleted_count = (
            db.query(DataSourceItem)
            .filter(DataSourceItem.data_source_id == uuid.UUID(data_source_id), DataSourceItem.created_at < cutoff_date)
            .delete()
        )

        db.commit()

        logger.info(f"✅ Deleted {deleted_count} old items from data source {data_source_id}")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "data_source_id": data_source_id,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as exc:
        logger.error(f"❌ Error cleaning up data source {data_source_id}: {exc}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(exc)}

    finally:
        db.close()
