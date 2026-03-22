"""
Usage Analytics model.

This module defines the usage analytics model for tracking platform usage metrics.
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class UsageAnalytics(BaseModel):
    """
    Usage Analytics model.

    Tracks daily usage metrics for analytics and reporting.
    """

    __tablename__ = "usage_analytics"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Agent ID (null for tenant-wide metrics)",
    )

    date = Column(
        Date,
        nullable=False,
        index=True,
        comment="Date of the metrics",
    )

    metric_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of metric (e.g., chat_messages, file_uploads, api_calls)",
    )

    total_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total count of the metric",
    )

    credits_consumed = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total credits consumed for this metric",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="usage_analytics",
    )

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="usage_analytics",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UsageAnalytics(id={self.id}, metric={self.metric_type}, count={self.total_count})>"

    @classmethod
    def get_or_create(
        cls,
        session,
        tenant_id: UUID,
        metric_type: str,
        analytics_date: date,
        agent_id: UUID = None,
    ) -> "UsageAnalytics":
        """Get or create usage analytics record for a specific date and metric."""
        record = (
            session.query(cls)
            .filter_by(
                tenant_id=tenant_id,
                agent_id=agent_id,
                date=analytics_date,
                metric_type=metric_type,
            )
            .first()
        )

        if not record:
            record = cls(
                tenant_id=tenant_id,
                agent_id=agent_id,
                date=analytics_date,
                metric_type=metric_type,
                total_count=0,
                credits_consumed=0,
            )
            session.add(record)
            session.flush()

        return record

    def increment(self, count: int = 1, credits: int = 0) -> None:
        """Increment usage metrics."""
        self.total_count += count
        self.credits_consumed += credits
