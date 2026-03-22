"""
Credit deduction utility functions for chat operations.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.credit_transaction import ActionType
from src.services.billing.credit_service import CreditService


def get_chat_action_type(model_name: str) -> ActionType:
    """
    Determine action type based on LLM model.

    Args:
        model_name: Name of the LLM model

    Returns:
        ActionType enum value for the model
    """
    model_lower = model_name.lower()
    if "gpt-4" in model_lower:
        return ActionType.CHAT_MESSAGE_GPT4
    elif "gpt-3.5" in model_lower or "gpt-35" in model_lower:
        return ActionType.CHAT_MESSAGE_GPT35
    elif "claude" in model_lower:
        return ActionType.CHAT_MESSAGE_CLAUDE
    elif "gemini" in model_lower:
        return ActionType.CHAT_MESSAGE_GEMINI
    else:
        return ActionType.CHAT_MESSAGE_GPT35  # Default


async def check_sufficient_credits(
    db: AsyncSession, tenant_id: uuid.UUID, action_type: ActionType
) -> tuple[bool, int, int]:
    """
    Check if tenant has sufficient credits for an action.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        action_type: Type of action requiring credits

    Returns:
        Tuple of (has_sufficient, available_credits, required_amount)
    """
    credit_service = CreditService(db)
    available = await credit_service.get_available_credits(tenant_id)
    required = ActionType.get_credit_cost(action_type)

    return (available >= required, available, required)
