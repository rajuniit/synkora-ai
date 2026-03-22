"""
Credit Enforcement Middleware

This middleware enforces credit limits and tracks credit usage across the platform.
It intercepts requests to check credit availability and deducts credits after actions.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.credit_transaction import ActionType
from src.services.billing import CreditService

logger = logging.getLogger(__name__)


class CreditMiddleware:
    """Middleware for credit enforcement and tracking"""

    # Credit costs for different actions
    CREDIT_COSTS = {
        ActionType.CHAT_MESSAGE_GPT35: 1,
        ActionType.CHAT_MESSAGE_GPT4: 5,
        ActionType.CHAT_MESSAGE_CLAUDE: 4,
        ActionType.STREAMING_RESPONSE: 0.5,
        ActionType.FILE_UPLOAD: 2,
        ActionType.IMAGE_ANALYSIS: 3,
        ActionType.VOICE_TTS: 2,  # Per minute
        ActionType.VOICE_STT: 1,  # Per minute
        ActionType.KNOWLEDGE_BASE_QUERY: 1,
        ActionType.CUSTOM_TOOL_EXECUTION: 2,
        ActionType.DATABASE_QUERY: 1,
        ActionType.CHART_GENERATION: 2,
        ActionType.API_CALL_EXTERNAL: 3,
    }

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.credit_service = CreditService(db_session)

    async def check_credits_before_action(
        self, tenant_id: UUID, action_type: ActionType, metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        Check if tenant has sufficient credits before performing an action

        Args:
            tenant_id: Tenant UUID
            action_type: Type of action being performed
            metadata: Additional metadata for cost calculation

        Returns:
            bool: True if sufficient credits, False otherwise

        Raises:
            HTTPException: If insufficient credits
        """
        try:
            # Calculate required credits
            required_credits = await self.calculate_action_cost(action_type, metadata)

            # Check if tenant has sufficient credits
            has_credits = await self.credit_service.check_sufficient_credits(
                tenant_id=tenant_id, required=required_credits
            )

            if not has_credits:
                balance = await self.credit_service.get_balance(tenant_id)
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "insufficient_credits",
                        "message": "Insufficient credits to perform this action",
                        "required_credits": required_credits,
                        "available_credits": balance.available_credits,
                        "action_type": action_type.value,
                    },
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking credits: {str(e)}")
            # Don't block the request on credit check errors
            return True

    async def deduct_credits_after_action(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        agent_id: UUID | None,
        action_type: ActionType,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Deduct credits after an action is performed

        Args:
            tenant_id: Tenant UUID
            user_id: User UUID (optional)
            agent_id: Agent UUID (optional)
            action_type: Type of action performed
            metadata: Additional metadata for the transaction

        Returns:
            bool: True if credits deducted successfully
        """
        try:
            # Calculate credits to deduct
            credits_amount = await self.calculate_action_cost(action_type, metadata)

            # Deduct credits
            success = await self.credit_service.deduct_credits(
                tenant_id=tenant_id,
                user_id=user_id,
                agent_id=agent_id,
                amount=credits_amount,
                action_type=action_type,
                metadata=metadata,
            )

            if not success:
                logger.warning(f"Failed to deduct credits for tenant {tenant_id}, action: {action_type.value}")

            return success

        except Exception as e:
            logger.error(f"Error deducting credits: {str(e)}")
            # Don't fail the request if credit deduction fails
            return False

    async def calculate_action_cost(self, action_type: ActionType, metadata: dict[str, Any] | None = None) -> int:
        """
        Calculate the credit cost for an action

        Args:
            action_type: Type of action
            metadata: Additional metadata for cost calculation

        Returns:
            int: Number of credits required
        """
        base_cost = self.CREDIT_COSTS.get(action_type, 1)

        # Apply multipliers based on metadata
        if metadata:
            # For streaming responses, add extra cost
            if metadata.get("streaming", False):
                base_cost += self.CREDIT_COSTS.get(ActionType.STREAMING_RESPONSE, 0.5)

            # For voice actions, multiply by duration in minutes
            if action_type in [ActionType.VOICE_TTS, ActionType.VOICE_STT]:
                duration_minutes = metadata.get("duration_minutes", 1)
                base_cost *= duration_minutes

            # For agent usage, add agent-specific costs
            if metadata.get("agent_id"):
                agent_cost = metadata.get("agent_credit_cost", 0)
                base_cost += agent_cost

        return int(base_cost)

    async def handle_insufficient_credits(
        self, request: Request, tenant_id: UUID, required_credits: int, available_credits: int
    ) -> JSONResponse:
        """
        Handle insufficient credits error

        Args:
            request: FastAPI request
            tenant_id: Tenant UUID
            required_credits: Credits required for action
            available_credits: Credits currently available

        Returns:
            JSONResponse: Error response
        """
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "error": "insufficient_credits",
                "message": "You don't have enough credits to perform this action",
                "required_credits": required_credits,
                "available_credits": available_credits,
                "tenant_id": str(tenant_id),
                "upgrade_url": "/billing/plans",
                "topup_url": "/billing/topup",
            },
        )

    async def get_credit_usage_summary(self, tenant_id: UUID, period: str = "current_month") -> dict[str, Any]:
        """
        Get credit usage summary for a tenant

        Args:
            tenant_id: Tenant UUID
            period: Time period for summary

        Returns:
            dict: Usage summary
        """
        try:
            balance = await self.credit_service.get_balance(tenant_id)

            return {
                "total_credits": balance.total_credits,
                "used_credits": balance.used_credits,
                "available_credits": balance.available_credits,
                "usage_percentage": (
                    (balance.used_credits / balance.total_credits * 100) if balance.total_credits > 0 else 0
                ),
                "last_reset_at": balance.last_reset_at.isoformat() if balance.last_reset_at else None,
                "next_reset_at": balance.next_reset_at.isoformat() if balance.next_reset_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting credit usage summary: {str(e)}")
            return {}


async def check_credits_decorator(
    tenant_id: UUID, action_type: ActionType, db_session: AsyncSession, metadata: dict[str, Any] | None = None
):
    """
    Decorator function to check credits before an action

    Usage:
        await check_credits_decorator(
            tenant_id=tenant_id,
            action_type=ActionType.CHAT_MESSAGE_GPT4,
            db_session=db,
            metadata={"streaming": True}
        )
    """
    middleware = CreditMiddleware(db_session)
    return await middleware.check_credits_before_action(tenant_id=tenant_id, action_type=action_type, metadata=metadata)


async def deduct_credits_decorator(
    tenant_id: UUID,
    action_type: ActionType,
    db_session: AsyncSession,
    user_id: UUID | None = None,
    agent_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Decorator function to deduct credits after an action

    Usage:
        await deduct_credits_decorator(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            action_type=ActionType.CHAT_MESSAGE_GPT4,
            db_session=db,
            metadata={"streaming": True, "tokens": 1500}
        )
    """
    middleware = CreditMiddleware(db_session)
    return await middleware.deduct_credits_after_action(
        tenant_id=tenant_id, user_id=user_id, agent_id=agent_id, action_type=action_type, metadata=metadata
    )
