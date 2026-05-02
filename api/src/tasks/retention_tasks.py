"""Data retention cleanup tasks.

Enforces configurable data retention policies for conversations, messages, and
uploaded files.  All tasks are registered in Celery beat and run weekly.

Configuration (env vars)
------------------------
CONVERSATION_RETENTION_DAYS  – default 365
MESSAGE_RETENTION_DAYS       – default 365 (also deletes messages whose
                                conversation no longer exists)
FILE_RETENTION_DAYS          – default 90
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from src.celery_app import celery_app
from src.core.database import get_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.cleanup_old_conversations")
def cleanup_old_conversations() -> dict[str, Any]:
    """Delete conversations older than CONVERSATION_RETENTION_DAYS (default: 365).

    Cascades: dependent messages must be deleted first by the sibling task
    ``cleanup_old_messages``, or this task will handle orphaned messages via
    the ON DELETE CASCADE defined on the FK — if no cascade exists at the DB
    level, messages are deleted here as well.
    """
    retention_days = int(os.getenv("CONVERSATION_RETENTION_DAYS", "365"))
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    db = next(get_db())
    deleted_count = 0
    try:
        from src.models.conversation import Conversation
        from src.models.message import Message

        # Collect IDs first to avoid large DELETE without index support
        old_conv_ids = [
            row.id for row in db.query(Conversation.id).filter(Conversation.created_at < cutoff).limit(10000).all()
        ]

        if old_conv_ids:
            # Delete child messages first (in case no FK cascade)
            msg_count = (
                db.query(Message).filter(Message.conversation_id.in_(old_conv_ids)).delete(synchronize_session=False)
            )
            logger.info(
                "Retention: deleted %d messages from %d old conversations",
                msg_count,
                len(old_conv_ids),
            )

            deleted_count = (
                db.query(Conversation).filter(Conversation.id.in_(old_conv_ids)).delete(synchronize_session=False)
            )

        db.commit()
        logger.info(
            "Retention cleanup_old_conversations: deleted=%d retention_days=%d",
            deleted_count,
            retention_days,
        )
        return {
            "status": "success",
            "deleted_conversations": deleted_count,
            "retention_days": retention_days,
        }

    except Exception as exc:
        logger.exception("Retention cleanup_old_conversations failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.cleanup_old_messages")
def cleanup_old_messages() -> dict[str, Any]:
    """Delete messages that are:

    1. Older than MESSAGE_RETENTION_DAYS (default: 365), **or**
    2. Orphaned — their parent conversation no longer exists.
    """
    retention_days = int(os.getenv("MESSAGE_RETENTION_DAYS", "365"))
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    db = next(get_db())
    deleted_count = 0
    try:
        from sqlalchemy import text

        from src.models.conversation import Conversation
        from src.models.message import Message

        # 1. Messages older than the retention window
        deleted_old = db.query(Message).filter(Message.created_at < cutoff).delete(synchronize_session=False)

        # 2. Orphaned messages (conversation deleted without cascading)
        existing_conv_ids_subq = db.query(Conversation.id).scalar_subquery()
        deleted_orphan = (
            db.query(Message)
            .filter(Message.conversation_id.not_in(existing_conv_ids_subq))
            .delete(synchronize_session=False)
        )

        deleted_count = deleted_old + deleted_orphan
        db.commit()

        logger.info(
            "Retention cleanup_old_messages: deleted=%d (aged=%d orphaned=%d) retention_days=%d",
            deleted_count,
            deleted_old,
            deleted_orphan,
            retention_days,
        )
        return {
            "status": "success",
            "deleted_messages": deleted_count,
            "deleted_aged": deleted_old,
            "deleted_orphaned": deleted_orphan,
            "retention_days": retention_days,
        }

    except Exception as exc:
        logger.exception("Retention cleanup_old_messages failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.cleanup_old_files")
def cleanup_old_files() -> dict[str, Any]:
    """Delete uploaded files older than FILE_RETENTION_DAYS (default: 90).

    Only the DB record is removed here.  Object storage (S3/MinIO) cleanup
    should be handled by a lifecycle rule on the bucket, or can be added here
    by calling the storage service before deletion.
    """
    retention_days = int(os.getenv("FILE_RETENTION_DAYS", "90"))
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    db = next(get_db())
    deleted_count = 0
    try:
        from src.models.upload_file import UploadFile

        deleted_count = db.query(UploadFile).filter(UploadFile.created_at < cutoff).delete(synchronize_session=False)
        db.commit()

        logger.info(
            "Retention cleanup_old_files: deleted=%d retention_days=%d",
            deleted_count,
            retention_days,
        )
        return {
            "status": "success",
            "deleted_files": deleted_count,
            "retention_days": retention_days,
        }

    except Exception as exc:
        logger.exception("Retention cleanup_old_files failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()
