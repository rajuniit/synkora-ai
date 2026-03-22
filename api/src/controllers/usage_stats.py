"""
Usage statistics controller
"""

import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.services.billing import CreditService, PlanRestrictionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usage-stats", tags=["usage-stats"])


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics"""

    plan_name: str
    plan_tier: str
    limits: dict[str, Any]
    current_usage: dict[str, int]
    usage_percentage: dict[str, float]
    credit_balance: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=UsageStatsResponse)
async def get_usage_stats(
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Get current usage statistics for the tenant's subscription plan.

    Returns:
    - Plan name and tier
    - Plan limits for agents, team members, and API calls
    - Current usage counts
    - Usage percentage for each resource
    """
    try:
        restriction_service = PlanRestrictionService(db)
        credit_service = CreditService(db)

        # Get plan details
        plan = await restriction_service.get_tenant_plan(tenant_id)

        # Get current usage
        agent_count = await restriction_service.get_agent_count(tenant_id)
        team_member_count = await restriction_service.get_team_member_count(tenant_id)
        api_calls_count = await restriction_service.get_api_calls_count(tenant_id)

        # Get credit balance
        credit_balance = await credit_service.get_balance(tenant_id)

        # Calculate usage percentages
        agent_percentage = (agent_count / plan.max_agents * 100) if plan.max_agents else 0
        team_member_percentage = (team_member_count / plan.max_team_members * 100) if plan.max_team_members else 0
        api_calls_percentage = (
            (api_calls_count / plan.max_api_calls_per_month * 100) if plan.max_api_calls_per_month else 0
        )

        return UsageStatsResponse(
            plan_name=plan.name,
            plan_tier=plan.tier,
            limits={
                "max_agents": plan.max_agents,
                "max_team_members": plan.max_team_members,
                "max_api_calls_per_month": plan.max_api_calls_per_month,
                "max_knowledge_bases": plan.max_knowledge_bases,
                "max_data_sources": plan.max_data_sources,
                "max_custom_tools": plan.max_custom_tools,
                "max_database_connections": plan.max_database_connections,
                "max_mcp_servers": plan.max_mcp_servers,
                "max_scheduled_tasks": plan.max_scheduled_tasks,
                "max_widgets": plan.max_widgets,
                "max_slack_bots": plan.max_slack_bots,
                "features": plan.features or {},
            },
            current_usage={
                "agents": agent_count,
                "team_members": team_member_count,
                "api_calls_this_month": api_calls_count,
            },
            usage_percentage={
                "agents": round(agent_percentage, 2),
                "team_members": round(team_member_percentage, 2),
                "api_calls": round(api_calls_percentage, 2),
            },
            credit_balance=credit_balance,
        )

    except Exception as e:
        logger.error(f"Error getting usage stats: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get usage statistics")
