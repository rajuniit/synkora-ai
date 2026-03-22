"""
Credit Balance model.

This module defines the credit balance model for tracking tenant credit balances.
"""

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class CreditBalance(BaseModel):
    """
    Credit Balance model.

    Tracks the current credit balance for each tenant.
    """

    __tablename__ = "credit_balances"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Tenant ID",
    )

    total_credits = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total credits allocated",
    )

    used_credits = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Credits consumed",
    )

    available_credits = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Available credits (computed field)",
    )

    last_reset_at = Column(
        sa.DateTime(timezone=True),
        nullable=True,
        comment="Last time credits were reset",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="credit_balance",
    )

    transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction",
        back_populates="credit_balance",
        order_by="CreditTransaction.created_at.desc()",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CreditBalance(id={self.id}, tenant_id={self.tenant_id}, available={self.available_credits})>"

    @property
    def has_credits(self) -> bool:
        """Check if tenant has available credits."""
        return self.available_credits > 0

    def can_deduct(self, amount: int) -> bool:
        """Check if tenant has enough credits for a transaction."""
        return self.available_credits >= amount
