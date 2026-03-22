"""
Credit Top-up model.

This module defines the credit top-up model for tracking credit purchases.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class TopupStatus(StrEnum):
    """Top-up payment status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class CreditTopup(BaseModel):
    """
    Credit Top-up model.

    Tracks credit purchases and top-ups.
    """

    __tablename__ = "credit_topups"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )

    credits = Column(
        Integer,
        nullable=False,
        comment="Number of credits purchased",
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Amount paid in currency (e.g., USD)",
    )

    status = Column(
        SQLEnum(TopupStatus),
        nullable=False,
        default=TopupStatus.PENDING,
        index=True,
        comment="Payment status",
    )

    payment_method = Column(
        String(50),
        nullable=True,
        comment="Payment method (e.g., stripe, paddle)",
    )

    payment_provider = Column(
        String(20),
        nullable=False,
        default="stripe",
        index=True,
        comment="Payment provider: 'stripe' or 'paddle'",
    )

    stripe_payment_intent_id = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Stripe payment intent ID",
    )

    paddle_transaction_id = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Paddle transaction ID",
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the topup was completed",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="credit_topups",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CreditTopup(id={self.id}, credits={self.credits}, status={self.status})>"

    @property
    def is_completed(self) -> bool:
        """Check if top-up is completed."""
        return self.status == TopupStatus.COMPLETED

    @property
    def is_pending(self) -> bool:
        """Check if top-up is pending."""
        return self.status == TopupStatus.PENDING

    @property
    def is_failed(self) -> bool:
        """Check if top-up failed."""
        return self.status == TopupStatus.FAILED

    @property
    def price_per_credit(self) -> Decimal:
        """Calculate price per credit."""
        if self.credits > 0:
            return Decimal(str(self.amount)) / Decimal(str(self.credits))
        return Decimal("0")

    def mark_as_completed(
        self, stripe_payment_intent_id: str | None = None, paddle_transaction_id: str | None = None
    ) -> None:
        """Mark top-up as completed."""
        self.status = TopupStatus.COMPLETED
        if stripe_payment_intent_id:
            self.stripe_payment_intent_id = stripe_payment_intent_id
            self.payment_provider = "stripe"
        if paddle_transaction_id:
            self.paddle_transaction_id = paddle_transaction_id
            self.payment_provider = "paddle"
        self.completed_at = datetime.now(UTC)

    def mark_as_failed(self) -> None:
        """Mark top-up as failed."""
        self.status = TopupStatus.FAILED
