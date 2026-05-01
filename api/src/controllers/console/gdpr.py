"""
GDPR compliance endpoints.

Article 15 — Right of Access / DSAR:
  POST /console/api/account/export-data  — request full personal data export

Article 17 — Right to Erasure:
  POST /console/api/account/erase-data  — request erasure of own data
  GET  /console/api/account/erase-data  — check status of latest erasure request
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.erasure_request import ErasureRequest
from src.models.tenant import Account, AccountRole

# ---------------------------------------------------------------------------
# Response schemas (Article 15 — data export)
# ---------------------------------------------------------------------------


class DataExportResponse(BaseModel):
    """Response body for the data export request."""

    message: str
    request_id: str


logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Article 15 — POST /console/api/account/export-data
# ---------------------------------------------------------------------------


@router.post(
    "/export-data",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a full personal data export (GDPR Article 15 / DSAR)",
)
async def request_data_export(
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
) -> DataExportResponse:
    """
    Queue a background Celery task that collects all personal data for the
    authenticated account and emails a download link when ready.

    Returns 202 Accepted immediately with a request_id for reference.
    """
    from src.tasks.gdpr_tasks import export_account_data

    request_id = str(uuid.uuid4())

    export_account_data.delay(
        str(current_account.id),
        str(tenant_id),
        request_id,
    )

    logger.info(
        "GDPR data export requested: account=%s tenant=%s request_id=%s",
        current_account.id,
        tenant_id,
        request_id,
    )

    return DataExportResponse(
        message="Export started. You will receive an email when ready.",
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# Response schemas (Article 17 — erasure)
# ---------------------------------------------------------------------------


class ErasureRequestResponse(BaseModel):
    """Response body for erasure request endpoints."""

    id: str
    account_id: str
    status: str
    created_at: str
    completed_at: str | None
    error_message: str | None
    erased_summary: str | None


# ---------------------------------------------------------------------------
# POST /console/api/account/erase-data
# ---------------------------------------------------------------------------


@router.post(
    "/erase-data",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request erasure of own account data (GDPR Article 17)",
)
async def request_erasure(
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
) -> ErasureRequestResponse:
    """
    Dispatch a background task to hard-delete all personal data for the
    authenticated account within the current tenant.

    Rate limited to one request per 24 hours.  Returns 202 Accepted with the
    erasure request record.
    """
    from src.tasks.gdpr_tasks import erase_account_data

    account_id = current_account.id

    # ------------------------------------------------------------------
    # Rate-limit: reject if a request was already submitted in the last 24 h
    # ------------------------------------------------------------------
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    result = await db.execute(
        select(ErasureRequest)
        .where(
            ErasureRequest.account_id == account_id,
            ErasureRequest.status.in_(["pending", "processing", "completed"]),
            ErasureRequest.created_at >= cutoff,
        )
        .order_by(ErasureRequest.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"An erasure request was already submitted recently (id={existing.id}, "
                f"status={existing.status}). Please wait 24 hours before submitting another."
            ),
        )

    # ------------------------------------------------------------------
    # Create the erasure request record with status="processing" so the
    # record is committed in its in-flight state before the Celery task
    # is dispatched.  This closes the race window where a concurrent
    # request or a task retry could observe status="pending" and start a
    # second erasure run.
    # ------------------------------------------------------------------
    erasure = ErasureRequest(
        account_id=account_id,
        tenant_id=tenant_id,
        requested_by=account_id,
        status="processing",
    )
    db.add(erasure)
    await db.commit()
    await db.refresh(erasure)

    # ------------------------------------------------------------------
    # Dispatch the Celery task asynchronously — the DB row is already
    # committed as "processing" before the worker can start.
    # ------------------------------------------------------------------
    erase_account_data.delay(
        str(account_id),
        str(tenant_id),
        str(account_id),
    )

    logger.info(f"GDPR erasure requested: account={account_id} tenant={tenant_id} request_id={erasure.id}")

    return ErasureRequestResponse(
        id=str(erasure.id),
        account_id=str(erasure.account_id),
        status=erasure.status,
        created_at=erasure.created_at.isoformat(),
        completed_at=erasure.completed_at.isoformat() if erasure.completed_at else None,
        error_message=erasure.error_message,
        erased_summary=erasure.erased_summary,
    )


# ---------------------------------------------------------------------------
# GET /console/api/account/erase-data
# ---------------------------------------------------------------------------


@router.get(
    "/erase-data",
    summary="Check the status of the latest GDPR erasure request",
)
async def get_erasure_status(
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
) -> ErasureRequestResponse:
    """
    Return the most recent erasure request for the authenticated account.
    Returns 404 if no request has ever been submitted.
    """
    result = await db.execute(
        select(ErasureRequest)
        .where(
            ErasureRequest.account_id == current_account.id,
            ErasureRequest.tenant_id == tenant_id,
        )
        .order_by(ErasureRequest.created_at.desc())
        .limit(1)
    )
    erasure = result.scalar_one_or_none()

    if not erasure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No erasure request found for this account.",
        )

    return ErasureRequestResponse(
        id=str(erasure.id),
        account_id=str(erasure.account_id),
        status=erasure.status,
        created_at=erasure.created_at.isoformat(),
        completed_at=erasure.completed_at.isoformat() if erasure.completed_at else None,
        error_message=erasure.error_message,
        erased_summary=erasure.erased_summary,
    )
