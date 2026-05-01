"""GDPR erasure request audit trail."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class ErasureRequest(BaseModel):
    """
    GDPR Article 17 right-to-erasure request.

    Stores the audit trail for all erasure requests. The account_id column
    intentionally has no FK constraint — the account row may be anonymised
    (not deleted) after erasure, and this record must survive that change.
    """

    __tablename__ = "erasure_requests"

    # No FK to accounts — account may be anonymised after erasure
    account_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # UUID of whoever initiated the request (account itself, or an admin)
    requested_by = Column(UUID(as_uuid=True), nullable=False)

    # pending → processing → completed | failed
    status = Column(String(20), nullable=False, default="pending", index=True)

    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Human-readable summary of what was erased (counts per entity type)
    erased_summary = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ErasureRequest(id={self.id}, account_id={self.account_id}, status={self.status})>"
