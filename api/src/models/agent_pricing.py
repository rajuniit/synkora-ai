"""
Agent Pricing model.

This module defines the agent pricing model for agent monetization.
"""

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class PricingModel(StrEnum):
    """Agent pricing models."""

    FREE = "FREE"
    PER_USE = "PER_USE"
    SUBSCRIPTION = "SUBSCRIPTION"


class AgentPricing(BaseModel):
    """
    Agent Pricing model.

    Defines monetization settings for agents.
    """

    __tablename__ = "agent_pricing"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Agent ID",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Creator tenant ID",
    )

    pricing_model = Column(
        SQLEnum(PricingModel),
        nullable=False,
        default=PricingModel.FREE,
        index=True,
        comment="Pricing model type",
    )

    credits_per_use = Column(
        Integer,
        nullable=True,
        comment="Credits charged per use (for PER_USE model)",
    )

    monthly_subscription_credits = Column(
        Integer,
        nullable=True,
        comment="Monthly subscription cost in credits",
    )

    revenue_share_percentage = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("70.00"),
        comment="Creator revenue share percentage (e.g., 70.00 for 70%)",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether pricing is active",
    )

    total_uses = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of uses",
    )

    total_revenue_credits = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total revenue earned in credits",
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="pricing",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="agent_pricing",
    )

    revenue_records: Mapped[list["AgentRevenue"]] = relationship(
        "AgentRevenue",
        back_populates="agent_pricing",
        order_by="AgentRevenue.created_at.desc()",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentPricing(id={self.id}, agent_id={self.agent_id}, model={self.pricing_model})>"

    @property
    def is_free(self) -> bool:
        """Check if agent is free to use."""
        return self.pricing_model == PricingModel.FREE

    @property
    def is_paid(self) -> bool:
        """Check if agent requires payment."""
        return self.pricing_model in (PricingModel.PER_USE, PricingModel.SUBSCRIPTION)

    def calculate_creator_revenue(self, amount: int) -> int:
        """Calculate creator's share of revenue."""
        return int(amount * float(self.revenue_share_percentage) / 100)

    def calculate_platform_revenue(self, amount: int) -> int:
        """Calculate platform's share of revenue."""
        return amount - self.calculate_creator_revenue(amount)
