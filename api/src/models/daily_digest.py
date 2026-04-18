"""Daily digest model for pre-computed data source summaries."""

import uuid
from datetime import date as DateType
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import BaseModel, TenantMixin


class DigestStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DailyDigest(TenantMixin, BaseModel):
    """
    Pre-computed daily summary for a data source.

    Generated nightly by a Celery beat task. Agents query this table
    for scheduled summaries instead of hitting external APIs directly.
    """

    __tablename__ = "daily_digests"

    data_source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    digest_date: Mapped[DateType] = mapped_column(Date, nullable=False)
    structured_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DigestStatus.PENDING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("data_source_id", "digest_date", name="uq_daily_digest_source_date"),
        Index("ix_daily_digests_tenant_date", "tenant_id", "digest_date"),
        Index("ix_daily_digests_status", "status"),
    )
