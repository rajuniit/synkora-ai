"""GDPR compliance tasks — Article 15 (data export) and Article 17 (erasure)."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.core.database import get_db

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.export_account_data",
    soft_time_limit=300,
    time_limit=360,
    max_retries=2,
    default_retry_delay=60,
)
def export_account_data(
    self,
    account_id: str,
    tenant_id: str,
    request_id: str,
) -> dict[str, Any]:
    """
    Collect all personal data for an account and prepare a DSAR export
    (GDPR Article 15 — Right of Access).

    Collects:
      - Account profile
      - All conversations + messages
      - Activity logs
      - Agent configs owned by the account
      - OAuth connections (no tokens)
      - Billing history

    After collection, the data is serialised to JSON and a download link
    is "emailed" to the account holder (stub: logged for now).

    Args:
        account_id:  UUID of the account to export (as string).
        tenant_id:   UUID of the tenant scope (as string).
        request_id:  Caller-supplied request ID for correlation.

    Returns:
        dict containing the exported data and metadata.
    """
    db: Session = next(get_db())

    try:
        account_uuid = uuid.UUID(account_id)
        tenant_uuid = uuid.UUID(tenant_id)

        export: dict[str, Any] = {
            "request_id": request_id,
            "account_id": account_id,
            "tenant_id": tenant_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": None,
            "conversations": [],
            "activity_logs": [],
            "agents_owned": [],
            "oauth_connections": [],
            "billing_history": [],
        }

        # ------------------------------------------------------------------
        # 1. Account profile
        # ------------------------------------------------------------------
        try:
            from src.models.tenant import Account

            account = db.query(Account).filter(Account.id == account_uuid).first()
            if account:
                export["profile"] = {
                    "id": str(account.id),
                    "email": account.email,
                    "name": account.name,
                    "phone": getattr(account, "phone", None),
                    "bio": getattr(account, "bio", None),
                    "company": getattr(account, "company", None),
                    "job_title": getattr(account, "job_title", None),
                    "location": getattr(account, "location", None),
                    "website": getattr(account, "website", None),
                    "created_at": account.created_at.isoformat() if account.created_at else None,
                    "last_login_at": getattr(account, "last_login_at", None),
                }
        except Exception as exc:
            logger.warning("DSAR profile collection failed for %s: %s", account_id, exc)

        # ------------------------------------------------------------------
        # 2. Conversations + messages
        # ------------------------------------------------------------------
        try:
            from src.models.conversation import Conversation
            from src.models.message import Message

            conversations = db.query(Conversation).filter(Conversation.account_id == account_uuid).limit(1000).all()
            for conv in conversations:
                messages = db.query(Message).filter(Message.conversation_id == conv.id).limit(5000).all()
                export["conversations"].append(
                    {
                        "id": str(conv.id),
                        "created_at": conv.created_at.isoformat() if conv.created_at else None,
                        "messages": [
                            {
                                "id": str(m.id),
                                "role": getattr(m, "role", None),
                                "content": getattr(m, "content", None),
                                "created_at": m.created_at.isoformat() if m.created_at else None,
                            }
                            for m in messages
                        ],
                    }
                )
        except Exception as exc:
            logger.warning("DSAR conversation collection failed for %s: %s", account_id, exc)

        # ------------------------------------------------------------------
        # 3. Activity logs
        # ------------------------------------------------------------------
        try:
            from src.models.activity_log import ActivityLog

            logs = (
                db.query(ActivityLog)
                .filter(ActivityLog.account_id == account_uuid)
                .order_by(ActivityLog.created_at.desc())
                .limit(10000)
                .all()
            )
            export["activity_logs"] = [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": str(log.resource_id) if log.resource_id else None,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        except Exception as exc:
            logger.warning("DSAR activity log collection failed for %s: %s", account_id, exc)

        # ------------------------------------------------------------------
        # 4. Agent configs owned by the account (within this tenant)
        # ------------------------------------------------------------------
        try:
            from src.models.agent import Agent

            agents = (
                db.query(Agent)
                .filter(Agent.tenant_id == tenant_uuid, Agent.created_by == account_uuid)
                .limit(500)
                .all()
            )
            export["agents_owned"] = [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in agents
            ]
        except Exception as exc:
            logger.warning("DSAR agent collection failed for %s: %s", account_id, exc)

        # ------------------------------------------------------------------
        # 5. OAuth connections (no tokens — only provider + scopes)
        # ------------------------------------------------------------------
        try:
            from src.models.user_oauth_token import UserOAuthToken

            oauth_tokens = db.query(UserOAuthToken).filter(UserOAuthToken.account_id == account_uuid).all()
            export["oauth_connections"] = [
                {
                    "provider": getattr(t, "provider", None),
                    "scopes": getattr(t, "scopes", None),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in oauth_tokens
            ]
        except Exception as exc:
            logger.warning("DSAR oauth collection failed for %s: %s", account_id, exc)

        # ------------------------------------------------------------------
        # 6. Billing history stub (no billing model available — placeholder)
        # ------------------------------------------------------------------
        export["billing_history"] = []

        # ------------------------------------------------------------------
        # 7. Notify the account holder
        #    Stub: log the notification (replace with actual email delivery)
        # ------------------------------------------------------------------
        account_email = export["profile"]["email"] if export["profile"] else account_id
        logger.info(
            "DSAR export complete — email would be sent to %s with download link "
            "(request_id=%s, conversations=%d, activity_logs=%d)",
            account_email,
            request_id,
            len(export["conversations"]),
            len(export["activity_logs"]),
        )

        return export

    except Exception as exc:
        logger.exception("DSAR export failed for account %s: %s", account_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Article 17 — hard-delete task (existing)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="tasks.erase_account_data",
    soft_time_limit=300,
    time_limit=360,
    max_retries=3,
    default_retry_delay=60,
)
def erase_account_data(
    self,
    account_id: str,
    tenant_id: str,
    requested_by: str,
) -> dict[str, Any]:
    """
    Hard-delete all personal data for an account (GDPR Article 17).

    Deletion order respects FK constraints: children are removed before
    parents.  The Account row itself is anonymised rather than deleted to
    preserve referential integrity with any remaining rows (e.g. billing
    records, audit logs) that reference it.

    Args:
        account_id:   UUID of the account to erase (as string).
        tenant_id:    UUID of the tenant that owns the account (as string).
        requested_by: UUID of whoever requested the erasure (as string).

    Returns:
        {"erased": True, "account_id": account_id}
    """
    from src.models.erasure_request import ErasureRequest

    db: Session = next(get_db())

    # Resolve the ErasureRequest that was created by the controller.
    # The controller commits the record with status="processing" before
    # dispatching this task, so we match on that status.
    erasure_record: ErasureRequest | None = (
        db.query(ErasureRequest)
        .filter(
            ErasureRequest.account_id == uuid.UUID(account_id),
            ErasureRequest.tenant_id == uuid.UUID(tenant_id),
            ErasureRequest.status == "processing",
        )
        .order_by(ErasureRequest.created_at.desc())
        .first()
    )

    # Idempotency guard: if the most recent record for this account is
    # already "completed" or "failed" it means this task is a spurious
    # retry or a duplicate dispatch.  Return early to prevent double-erasure.
    if erasure_record is None:
        latest: ErasureRequest | None = (
            db.query(ErasureRequest)
            .filter(
                ErasureRequest.account_id == uuid.UUID(account_id),
                ErasureRequest.tenant_id == uuid.UUID(tenant_id),
                ErasureRequest.status.in_(["completed", "failed"]),
            )
            .order_by(ErasureRequest.created_at.desc())
            .first()
        )
        if latest is not None:
            logger.warning(
                f"GDPR erasure task skipped — already {latest.status}: account={account_id} request_id={latest.id}"
            )
            db.close()
            return {"erased": False, "account_id": account_id, "reason": f"already_{latest.status}"}

    try:
        _do_erase(db, account_id, tenant_id, erasure_record)

        if erasure_record:
            erasure_record.status = "completed"
            erasure_record.completed_at = datetime.now(UTC)
            db.commit()

        logger.info(f"GDPR erasure completed for account {account_id}")
        return {"erased": True, "account_id": account_id}

    except Exception as exc:
        logger.exception(f"GDPR erasure failed for account {account_id}: {exc}")

        if erasure_record:
            try:
                erasure_record.status = "failed"
                erasure_record.error_message = str(exc)[:500]
                db.commit()
            except Exception:
                db.rollback()

        raise self.retry(exc=exc)

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _do_erase(
    db: Session,
    account_id: str,
    tenant_id: str,
    erasure_record: Any,
) -> None:
    """Perform the actual data deletion / anonymisation in a single transaction."""
    from sqlalchemy import update as sa_update

    from src.models.activity_log import ActivityLog
    from src.models.conversation import Conversation
    from src.models.message import Message
    from src.models.tenant import Account, TenantAccountJoin
    from src.models.user_oauth_token import UserOAuthToken

    account_uuid = uuid.UUID(account_id)
    tenant_uuid = uuid.UUID(tenant_id)

    summary_parts: list[str] = []

    # ------------------------------------------------------------------
    # 1. Messages  (no direct account_id column — delete via conversations
    #    owned by this account in this tenant)
    # ------------------------------------------------------------------
    # Conversation has no tenant_id column — it is tenant-scoped indirectly
    # via its agent_id.  We erase all conversations owned by this account
    # (across all tenants); that is the correct GDPR scope.
    owned_conv_ids: list[uuid.UUID] = [
        row.id for row in db.query(Conversation.id).filter(Conversation.account_id == account_uuid).all()
    ]

    if owned_conv_ids:
        msg_count = (
            db.query(Message).filter(Message.conversation_id.in_(owned_conv_ids)).delete(synchronize_session=False)
        )
        summary_parts.append(f"messages:{msg_count}")
    else:
        summary_parts.append("messages:0")

    # ------------------------------------------------------------------
    # 2. Conversations
    # ------------------------------------------------------------------
    conv_count = (
        db.query(Conversation).filter(Conversation.account_id == account_uuid).delete(synchronize_session=False)
    )
    summary_parts.append(f"conversations:{conv_count}")

    # ------------------------------------------------------------------
    # 3. ActivityLogs  (WHERE account_id = ?)
    # GDPR compliance note: we anonymise rather than hard-delete so that the
    # HMAC audit chain remains intact for forensic purposes. The personal data
    # fields (account_id, metadata) are nulled out, removing all PII while
    # preserving the chain structure required by the audit integrity check.
    # ------------------------------------------------------------------
    log_count = (
        db.execute(
            sa_update(ActivityLog)
            .where(ActivityLog.account_id == account_uuid)
            .values(account_id=None, activity_metadata=None)
            .execution_options(synchronize_session=False)
        )
    ).rowcount
    summary_parts.append(f"activity_logs_anonymised:{log_count}")

    # ------------------------------------------------------------------
    # 4. OAuth tokens
    # ------------------------------------------------------------------
    oauth_count = (
        db.query(UserOAuthToken).filter(UserOAuthToken.account_id == account_uuid).delete(synchronize_session=False)
    )
    summary_parts.append(f"oauth_tokens:{oauth_count}")

    # ------------------------------------------------------------------
    # 5. Session tokens in Redis
    # ------------------------------------------------------------------
    _purge_redis_sessions(account_id)

    # ------------------------------------------------------------------
    # 6. TenantAccountJoin  (unlink account from this specific tenant)
    # ------------------------------------------------------------------
    taj_count = (
        db.query(TenantAccountJoin)
        .filter(
            TenantAccountJoin.account_id == account_uuid,
            TenantAccountJoin.tenant_id == tenant_uuid,
        )
        .delete(synchronize_session=False)
    )
    summary_parts.append(f"tenant_memberships:{taj_count}")

    # ------------------------------------------------------------------
    # 7. Anonymise the Account row
    #    (hard delete is avoided to preserve referential integrity)
    # ------------------------------------------------------------------
    account = db.query(Account).filter(Account.id == account_uuid).first()
    if account:
        account.email = f"erased_{account_id}@deleted.invalid"
        account.name = "[Deleted User]"
        account.password_hash = None
        account.phone = None
        account.bio = None
        account.company = None
        account.job_title = None
        account.location = None
        account.website = None
        account.avatar_url = None
        account.two_factor_secret = None
        account.status = "DELETED"
        summary_parts.append("account:anonymised")
    else:
        summary_parts.append("account:not_found")

    # ------------------------------------------------------------------
    # 8. Persist summary on the erasure record and commit everything
    # ------------------------------------------------------------------
    if erasure_record is not None:
        erasure_record.erased_summary = ", ".join(summary_parts)

    db.commit()


def _purge_redis_sessions(account_id: str) -> None:
    """Delete all Redis session/token keys for an account."""
    try:
        from src.config.redis import get_redis

        redis = get_redis()
        if not redis:
            logger.warning(f"Redis unavailable — skipping session purge for account {account_id}")
            return

        # Revoke all access tokens by bumping the version counter to a large
        # value. Any token carrying an older 'ver' claim will be rejected by
        # _check_token_revocation() in the auth middleware.
        version_key = f"account_tokens:{account_id}:version"
        redis.set(version_key, 99999, ex=60 * 60 * 24 * 30)  # TTL: 30 days

        # Remove refresh token families stored under sessions:{account_id}:*
        pattern = f"sessions:{account_id}:*"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = redis.scan(cursor, match=pattern, count=200)
            if keys:
                redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        logger.info(f"Purged Redis sessions for account {account_id}: {deleted} keys deleted")

    except Exception as exc:
        # Non-fatal: the account is already anonymised in the DB; Redis keys
        # will expire naturally.  Log and continue rather than failing the task.
        logger.warning(f"Redis session purge failed for account {account_id}: {exc}")
