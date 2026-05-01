"""Audit log HMAC chain service.

Provides tamper-evident audit logging by chaining each entry's
HMAC to the previous entry's hash.
"""
import logging
import os
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Secret key for HMAC — prefer settings value so it is validated at startup;
# fall back to raw env var for contexts where settings aren't loaded yet
# (e.g. Alembic migration scripts).
try:
    from src.config.settings import settings as _settings  # noqa: PLC0415

    AUDIT_CHAIN_SECRET: str = _settings.audit_chain_secret or os.getenv("AUDIT_CHAIN_SECRET", "")
except Exception:
    AUDIT_CHAIN_SECRET = os.getenv("AUDIT_CHAIN_SECRET", "")

if not AUDIT_CHAIN_SECRET:
    logger.error(
        "CRITICAL: AUDIT_CHAIN_SECRET not set — tamper detection is DISABLED. "
        "Audit log entries will not be HMAC-chained and the chain cannot be verified. "
        "Set AUDIT_CHAIN_SECRET in your environment to enable tamper detection."
    )

GENESIS_HASH = "0" * 64  # The "previous hash" for the first entry


async def append_audit_log(
    db: AsyncSession,
    *,
    action: str,
    activity_type,   # ActivityType enum
    account_id=None,
    tenant_id=None,
    resource_type=None,
    resource_id=None,
    description=None,
    activity_metadata=None,
    ip_address=None,
    user_agent=None,
    status="success",
    error_message=None,
) -> "ActivityLog":
    """
    Create a chained audit log entry.

    Gets the previous entry's hash, computes this entry's hash,
    and persists both atomically.
    """
    from src.models.activity_log import ActivityLog

    # Get the most recent entry's hash for this tenant (chain is per-tenant)
    # Falls back to GENESIS_HASH if no prior entries exist
    prev_entry = None
    if tenant_id:
        result = await db.execute(
            select(ActivityLog)
            .filter(ActivityLog.tenant_id == tenant_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(1)
        )
        prev_entry = result.scalar_one_or_none()

    prev_hash = (prev_entry.entry_hash or GENESIS_HASH) if prev_entry else GENESIS_HASH

    # Create entry first to get the ID
    entry = ActivityLog.log_activity(
        action=action,
        activity_type=activity_type,
        account_id=account_id,
        tenant_id=tenant_id,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        activity_metadata=activity_metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        error_message=error_message,
    )
    db.add(entry)
    await db.flush()  # Get the ID without committing

    # Compute HMAC chain
    if AUDIT_CHAIN_SECRET:
        entry.entry_hash = ActivityLog.compute_hash(
            entry_id=str(entry.id),
            action=action,
            account_id=str(account_id) if account_id else None,
            tenant_id=str(tenant_id) if tenant_id else None,
            activity_type=str(activity_type),
            created_at=entry.created_at.isoformat() if entry.created_at else datetime.now(UTC).isoformat(),
            prev_hash=prev_hash,
            secret_key=AUDIT_CHAIN_SECRET,
        )
    else:
        logger.warning("AUDIT_CHAIN_SECRET not set — audit log entries will not be chained")

    return entry


async def verify_chain(db: AsyncSession, tenant_id, limit=1000) -> dict:
    """
    Verify the integrity of the audit log chain for a tenant.

    Returns {valid: bool, checked: int, first_broken_id: str | None}
    """
    from src.models.activity_log import ActivityLog

    if not AUDIT_CHAIN_SECRET:
        return {"valid": False, "checked": 0, "error": "AUDIT_CHAIN_SECRET not configured"}

    result = await db.execute(
        select(ActivityLog)
        .filter(ActivityLog.tenant_id == tenant_id)
        .order_by(ActivityLog.created_at.asc())
        .limit(limit)
    )
    entries = result.scalars().all()

    prev_hash = GENESIS_HASH
    for entry in entries:
        # NULL hash means the entry was never chained (pre-feature entry or hash
        # computation failure).  Treat it as a chain break — an attacker could
        # clear entry_hash to bypass HMAC verification.
        if entry.entry_hash is None:
            return {"valid": False, "checked": entries.index(entry), "first_broken_id": str(entry.id)}
        expected = ActivityLog.compute_hash(
            entry_id=str(entry.id),
            action=entry.action,
            account_id=str(entry.account_id) if entry.account_id else None,
            tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
            activity_type=str(entry.activity_type),
            created_at=entry.created_at.isoformat(),
            prev_hash=prev_hash,
            secret_key=AUDIT_CHAIN_SECRET,
        )
        if entry.entry_hash != expected:
            return {"valid": False, "checked": entries.index(entry), "first_broken_id": str(entry.id)}
        prev_hash = entry.entry_hash

    return {"valid": True, "checked": len(entries), "first_broken_id": None}
