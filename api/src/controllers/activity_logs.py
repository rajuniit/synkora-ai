"""
Activity logs controller
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.tenant import AccountRole
from src.services.activity.activity_log_service import ActivityLogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activity-logs", tags=["activity-logs"])


# Pydantic models for request/response
class ActivityLogResponse(BaseModel):
    id: int
    tenant_id: str
    account_id: str
    account_name: str
    account_email: str
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ActivityLogStats(BaseModel):
    total_activities: int
    unique_users: int
    top_actions: list[dict]
    recent_activities: list[ActivityLogResponse]


@router.get("", response_model=list[ActivityLogResponse])
async def list_activity_logs(
    account_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_date: datetime | None = Query(None, description="Filter logs from this date"),
    end_date: datetime | None = Query(None, description="Filter logs until this date"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """List activity logs for the current tenant"""
    try:
        activity_service = ActivityLogService(db)

        # Check if user has permission to view activity logs
        # Only owners and admins can view all logs
        from src.services.team.team_service import TeamService

        team_service = TeamService(db)
        current_member = await team_service.get_team_member(tenant_id, str(current_account.id))

        if not current_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Regular members can only see their own logs
        if current_member["role"] not in [AccountRole.OWNER.value, AccountRole.ADMIN.value]:
            account_id = str(current_account.id)

        logs = await activity_service.list_logs(
            tenant_id=tenant_id,
            account_id=account_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )

        return logs

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing activity logs: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list activity logs")


@router.get("/stats", response_model=ActivityLogStats)
async def get_activity_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get activity statistics for the current tenant"""
    try:
        activity_service = ActivityLogService(db)

        # Check if user has permission to view stats
        from src.services.team.team_service import TeamService

        team_service = TeamService(db)
        current_member = await team_service.get_team_member(tenant_id, str(current_account.id))

        if not current_member or current_member["role"] not in [AccountRole.OWNER.value, AccountRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to view activity statistics"
            )

        stats = await activity_service.get_stats(tenant_id, days)

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activity stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get activity statistics"
        )


@router.get("/{log_id}", response_model=ActivityLogResponse)
async def get_activity_log(
    log_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get a specific activity log"""
    try:
        activity_service = ActivityLogService(db)
        log = await activity_service.get_log(log_id)

        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity log not found")

        # Check tenant access
        if str(log.tenant_id) != str(tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Check if user has permission to view this log
        from src.services.team.team_service import TeamService

        team_service = TeamService(db)
        current_member = await team_service.get_team_member(tenant_id, str(current_account.id))

        if not current_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Regular members can only see their own logs
        if current_member["role"] not in [AccountRole.OWNER.value, AccountRole.ADMIN.value]:
            if str(log.account_id) != str(current_account.id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return log

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting activity log: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get activity log")


@router.get("/me/recent", response_model=list[ActivityLogResponse])
async def get_my_recent_activities(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get recent activities for the current user"""
    try:
        activity_service = ActivityLogService(db)
        logs = await activity_service.list_logs(
            tenant_id=tenant_id, account_id=str(current_account.id), skip=0, limit=limit
        )

        return logs

    except Exception as e:
        logger.error(f"Error getting recent activities: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get recent activities")


@router.delete("/cleanup", status_code=status.HTTP_204_NO_CONTENT)
async def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365, description="Delete logs older than this many days"),
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Clean up old activity logs"""
    try:
        # Check if user has permission to cleanup logs
        from src.services.team.team_service import TeamService

        team_service = TeamService(db)
        current_member = await team_service.get_team_member(tenant_id, str(current_account.id))

        if not current_member or current_member["role"] != AccountRole.OWNER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only tenant owners can cleanup activity logs"
            )

        activity_service = ActivityLogService(db)
        await activity_service.cleanup_old_logs(tenant_id, days)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cleanup activity logs")
