"""
Celery tasks for file and storage operations.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.celery_app import celery_app
from src.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="process_file_upload_task", bind=True, max_retries=3, default_retry_delay=60)
def process_file_upload_task(self, file_id: str, tenant_id: str, process_type: str = "default") -> dict[str, Any]:
    """
    Process an uploaded file (virus scan, extract metadata, generate thumbnails).

    Args:
        file_id: File UUID
        tenant_id: Tenant UUID
        process_type: Processing type (default, image, document, video)

    Returns:
        dict: Processing results
    """
    db = SessionLocal()

    try:
        from src.models.file import File
        from src.services.storage.file_processor import FileProcessor

        logger.info(f"📁 Processing file {file_id}")

        file = db.query(File).filter(File.id == uuid.UUID(file_id)).first()

        if not file:
            logger.error(f"File {file_id} not found")
            return {"success": False, "error": "File not found"}

        processor = FileProcessor(db)
        result = processor.process_file(file=file, process_type=process_type)

        # Update file status
        file.processing_status = "completed" if result.get("success") else "failed"
        file.processed_at = datetime.now(UTC)
        db.commit()

        logger.info(f"✅ File {file_id} processed successfully")

        return result

    except Exception as exc:
        logger.error(f"❌ Error processing file {file_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="generate_document_embeddings_task", bind=True, max_retries=3)
def generate_document_embeddings_task(self, document_id: str, knowledge_base_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Generate embeddings for a document in a knowledge base.

    Args:
        document_id: Document UUID
        knowledge_base_id: Knowledge base UUID
        tenant_id: Tenant UUID

    Returns:
        dict: Embedding generation results
    """
    db = SessionLocal()

    try:
        from src.services.knowledge_base.embedding_service import EmbeddingService

        logger.info(f"🔤 Generating embeddings for document {document_id}")

        embedding_service = EmbeddingService(db)
        result = embedding_service.generate_embeddings(
            document_id=uuid.UUID(document_id),
            knowledge_base_id=uuid.UUID(knowledge_base_id),
            tenant_id=uuid.UUID(tenant_id),
        )

        logger.info(f"✅ Embeddings generated for document {document_id}")

        return result

    except Exception as exc:
        logger.error(f"❌ Error generating embeddings: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=120 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="export_data_task", bind=True, max_retries=2)
def export_data_task(
    self, export_type: str, tenant_id: str, filters: dict[str, Any] | None = None, format: str = "csv"
) -> dict[str, Any]:
    """
    Export data to file (CSV, Excel, JSON, PDF).

    Args:
        export_type: Type of data to export (conversations, analytics, users, etc.)
        tenant_id: Tenant UUID
        filters: Optional filters for export
        format: Output format (csv, xlsx, json, pdf)

    Returns:
        dict: Export results with file URL
    """
    db = SessionLocal()

    try:
        from src.services.export.export_service import ExportService

        logger.info(f"📤 Exporting {export_type} data for tenant {tenant_id}")

        export_service = ExportService(db)
        result = export_service.export_data(
            export_type=export_type, tenant_id=uuid.UUID(tenant_id), filters=filters or {}, output_format=format
        )

        logger.info(f"✅ Data exported successfully: {result.get('file_url')}")

        return result

    except Exception as exc:
        logger.error(f"❌ Error exporting data: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=180 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="generate_report_task", bind=True, max_retries=2)
def generate_report_task(
    self, report_type: str, tenant_id: str, parameters: dict[str, Any] | None = None, format: str = "pdf"
) -> dict[str, Any]:
    """
    Generate a report (analytics, usage, billing, etc.).

    Args:
        report_type: Type of report (analytics, usage, billing, performance)
        tenant_id: Tenant UUID
        parameters: Report parameters (date range, filters, etc.)
        format: Output format (pdf, html, xlsx)

    Returns:
        dict: Report generation results with file URL
    """
    db = SessionLocal()

    try:
        from src.services.reports.report_generator import ReportGenerator

        logger.info(f"📊 Generating {report_type} report for tenant {tenant_id}")

        report_generator = ReportGenerator(db)
        result = report_generator.generate_report(
            report_type=report_type, tenant_id=uuid.UUID(tenant_id), parameters=parameters or {}, output_format=format
        )

        logger.info(f"✅ Report generated successfully: {result.get('file_url')}")

        return result

    except Exception as exc:
        logger.error(f"❌ Error generating report: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=180 * (2**self.request.retries))

    finally:
        db.close()


@celery_app.task(name="cleanup_temp_files_task")
def cleanup_temp_files_task(hours_old: int = 24) -> dict[str, Any]:
    """
    Clean up temporary files older than specified hours.

    Args:
        hours_old: Delete files older than this many hours

    Returns:
        dict: Cleanup results
    """
    db = SessionLocal()

    try:
        from src.models.file import File
        from src.services.storage.s3_storage import S3Storage

        logger.info(f"🧹 Cleaning up temp files older than {hours_old} hours")

        cutoff_time = datetime.now(UTC) - timedelta(hours=hours_old)

        # Find temporary files to delete
        temp_files = db.query(File).filter(File.is_temporary, File.created_at < cutoff_time).all()

        storage = S3Storage()
        deleted_count = 0
        failed_count = 0

        for file in temp_files:
            try:
                # Delete from storage
                storage.delete_file(file.storage_path)
                # Delete from database
                db.delete(file)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete file {file.id}: {e}")
                failed_count += 1

        db.commit()

        logger.info(f"✅ Cleaned up {deleted_count} temporary files")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "cutoff_time": cutoff_time.isoformat(),
        }

    except Exception as exc:
        logger.error(f"❌ Error cleaning up temp files: {exc}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(exc)}

    finally:
        db.close()


@celery_app.task(name="backup_database_task", bind=True, max_retries=1)
def backup_database_task(self, backup_type: str = "full", tenant_id: str | None = None) -> dict[str, Any]:
    """
    Create a database backup.

    Args:
        backup_type: Type of backup (full, incremental, tenant)
        tenant_id: Optional tenant ID for tenant-specific backup

    Returns:
        dict: Backup results with file location
    """
    try:
        from src.services.backup.backup_service import BackupService

        logger.info(f"💾 Creating {backup_type} database backup")

        backup_service = BackupService()
        result = backup_service.create_backup(
            backup_type=backup_type, tenant_id=uuid.UUID(tenant_id) if tenant_id else None
        )

        logger.info(f"✅ Backup created successfully: {result.get('backup_file')}")

        return result

    except Exception as exc:
        logger.error(f"❌ Error creating backup: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=600)  # 10 minutes


@celery_app.task(name="compress_files_task")
def compress_files_task(file_ids: list[str], archive_name: str, tenant_id: str) -> dict[str, Any]:
    """
    Compress multiple files into an archive.

    Args:
        file_ids: List of file UUIDs to compress
        archive_name: Name for the archive file
        tenant_id: Tenant UUID

    Returns:
        dict: Compression results with archive URL
    """
    db = SessionLocal()

    try:
        from src.services.storage.compression_service import CompressionService

        logger.info(f"🗜️ Compressing {len(file_ids)} files into {archive_name}")

        compression_service = CompressionService(db)
        result = compression_service.create_archive(
            file_ids=[uuid.UUID(fid) for fid in file_ids], archive_name=archive_name, tenant_id=uuid.UUID(tenant_id)
        )

        logger.info(f"✅ Files compressed successfully: {result.get('archive_url')}")

        return result

    except Exception as exc:
        logger.error(f"❌ Error compressing files: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

    finally:
        db.close()


@celery_app.task(name="scan_file_for_viruses_task", bind=True, max_retries=2)
def scan_file_for_viruses_task(self, file_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Scan a file for viruses and malware.

    Args:
        file_id: File UUID
        tenant_id: Tenant UUID

    Returns:
        dict: Scan results
    """
    db = SessionLocal()

    try:
        from src.models.file import File
        from src.services.security.virus_scanner import VirusScanner

        logger.info(f"🛡️ Scanning file {file_id} for viruses")

        file = db.query(File).filter(File.id == uuid.UUID(file_id)).first()

        if not file:
            return {"success": False, "error": "File not found"}

        scanner = VirusScanner()
        result = scanner.scan_file(file.storage_path)

        # Update file security status
        file.virus_scan_status = "clean" if result.get("is_clean") else "infected"
        file.virus_scan_date = datetime.now(UTC)
        db.commit()

        if not result.get("is_clean"):
            logger.warning(f"⚠️ Virus detected in file {file_id}: {result.get('threats')}")
        else:
            logger.info(f"✅ File {file_id} is clean")

        return result

    except Exception as exc:
        logger.error(f"❌ Error scanning file: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=120 * (2**self.request.retries))

    finally:
        db.close()
