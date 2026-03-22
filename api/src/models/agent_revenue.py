"""
Agent Revenue model.

This module defines the agent revenue model for tracking revenue distribution.
"""

from enum import StrEnum

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class RevenueStatus(StrEnum):
    """Revenue payment status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"


class AgentRevenue(BaseModel):
    """
    Agent Revenue model.

    Tracks revenue distribution for agent creators.
    """

    __tablename__ = "agent_revenue"

    agent_pricing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_pricing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent pricing ID",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Creator tenant ID",
    )

    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("credit_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related credit transaction ID",
    )

    total_credits = Column(
        Integer,
        nullable=False,
        comment="Total credits from transaction",
    )

    creator_credits = Column(
        Integer,
        nullable=False,
        comment="Credits allocated to creator",
    )

    platform_credits = Column(
        Integer,
        nullable=False,
        comment="Credits allocated to platform",
    )

    revenue_share_percentage = Column(
        Numeric(5, 2),
        nullable=False,
        comment="Revenue share percentage at time of transaction",
    )

    status = Column(
        SQLEnum(RevenueStatus),
        nullable=False,
        default=RevenueStatus.PENDING,
        index=True,
        comment="Payment status",
    )

    payout_reference = Column(
        String(255),
        nullable=True,
        comment="External payout reference (e.g., Stripe transfer ID)",
    )

    notes = Column(
        Text,
        nullable=True,
        comment="Additional notes",
    )

    # Relationships
    agent_pricing: Mapped["AgentPricing"] = relationship(
        "AgentPricing",
        back_populates="revenue_records",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="agent_revenues",
    )

    transaction: Mapped["CreditTransaction"] = relationship(
        "CreditTransaction",
        back_populates="agent_revenue",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentRevenue(id={self.id}, creator_credits={self.creator_credits}, status={self.status})>"

    @property
    def is_paid(self) -> bool:
        """Check if revenue has been paid out."""
        return self.status == RevenueStatus.PAID

    @property
    def is_pending(self) -> bool:
        """Check if revenue is pending payout."""
        return self.status == RevenueStatus.PENDING

    def mark_as_paid(self, payout_reference: str) -> None:
        """Mark revenue as paid."""
        self.status = RevenueStatus.PAID
        self.payout_reference = payout_reference

    def mark_as_failed(self, notes: str) -> None:
        """Mark revenue payout as failed."""
        self.status = RevenueStatus.FAILED
        self.notes = notes
