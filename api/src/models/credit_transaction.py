"""
Credit Transaction model.

This module defines the credit transaction model for tracking credit history.
"""

from enum import StrEnum

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship

from .base import BaseModel


class TransactionType(StrEnum):
    """Credit transaction types."""

    PURCHASE = "PURCHASE"
    SUBSCRIPTION_ALLOCATION = "SUBSCRIPTION_ALLOCATION"
    USAGE = "USAGE"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"
    AGENT_REVENUE = "AGENT_REVENUE"


class ActionType(StrEnum):
    """Action types for credit deduction."""

    # Generic actions
    CHAT_MESSAGE = "CHAT_MESSAGE"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    TOOL_USE = "TOOL_USE"
    FILE_UPLOAD = "FILE_UPLOAD"
    KNOWLEDGE_BASE_QUERY = "KNOWLEDGE_BASE_QUERY"

    # Model-specific chat actions
    CHAT_MESSAGE_GPT4 = "CHAT_MESSAGE_GPT4"
    CHAT_MESSAGE_GPT35 = "CHAT_MESSAGE_GPT35"
    CHAT_MESSAGE_CLAUDE = "CHAT_MESSAGE_CLAUDE"
    CHAT_MESSAGE_GEMINI = "CHAT_MESSAGE_GEMINI"

    @staticmethod
    def get_credit_cost(action_type: "ActionType") -> int:
        """
        Get credit cost for an action type.

        Simplified pricing model: Since customers use their own LLM API keys,
        platform costs are the same regardless of which model they use.
        1 credit = 1 platform action (message, tool use, KB query, etc.)
        File uploads cost 2 credits due to storage costs.
        """
        costs = {
            ActionType.CHAT_MESSAGE: 1,
            ActionType.AGENT_EXECUTION: 1,
            ActionType.TOOL_USE: 1,
            ActionType.FILE_UPLOAD: 2,  # Storage has real cost
            ActionType.KNOWLEDGE_BASE_QUERY: 1,
            # Model-specific costs (same for all - BYOK model)
            ActionType.CHAT_MESSAGE_GPT4: 1,
            ActionType.CHAT_MESSAGE_GPT35: 1,
            ActionType.CHAT_MESSAGE_CLAUDE: 1,
            ActionType.CHAT_MESSAGE_GEMINI: 1,
        }
        return costs.get(action_type, 1)


class CreditTransaction(BaseModel):
    """
    Credit Transaction model.

    Records all credit transactions for audit trail and history.
    """

    __tablename__ = "credit_transactions"

    credit_balance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("credit_balances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Credit balance ID",
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID",
    )

    transaction_type = Column(
        SQLEnum(TransactionType),
        nullable=False,
        index=True,
        comment="Type of transaction",
    )

    amount = Column(
        Integer,
        nullable=False,
        comment="Credit amount (positive for additions, negative for deductions)",
    )

    balance_after = Column(
        Integer,
        nullable=False,
        comment="Balance after this transaction",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Transaction description",
    )

    reference_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Reference to related entity (subscription, topup, etc.)",
    )

    reference_type = Column(
        String(50),
        nullable=True,
        comment="Type of referenced entity",
    )

    transaction_metadata = Column(
        Text,
        nullable=True,
        comment="Additional transaction metadata (JSON string)",
    )

    idempotency_key = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Idempotency key to prevent duplicate transactions",
    )

    # Relationships
    credit_balance: Mapped["CreditBalance"] = relationship(
        "CreditBalance",
        back_populates="transactions",
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="credit_transactions",
    )

    agent_revenue: Mapped["AgentRevenue"] = relationship(
        "AgentRevenue",
        back_populates="transaction",
        uselist=False,
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<CreditTransaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"

    @property
    def is_credit(self) -> bool:
        """Check if transaction adds credits."""
        return self.amount > 0

    @property
    def is_debit(self) -> bool:
        """Check if transaction deducts credits."""
        return self.amount < 0
