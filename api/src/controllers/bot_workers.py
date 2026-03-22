"""Bot Workers API controller.

Provides endpoints for monitoring and managing bot workers.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.redis import get_redis
from ..core.database import get_async_db
from ..middleware.auth_middleware import get_current_account
from ..models import Account
from ..services.bot_worker.bot_deployment_service import BotDeploymentService
from ..services.bot_worker.worker_registry import WorkerRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bot-workers", tags=["bot-workers"])


# ==================== Response Models ====================


class WorkerStatusResponse(BaseModel):
    """Worker status response."""

    worker_id: str
    capacity: int
    active_bots: int
    started_at: float
    last_heartbeat: float
    is_healthy: bool
    utilization_percent: float
    host: str | None = None


class WorkerListResponse(BaseModel):
    """List of workers response."""

    workers: list[WorkerStatusResponse]
    total_workers: int
    healthy_workers: int


class CapacityResponse(BaseModel):
    """Worker pool capacity response."""

    total_capacity: int
    active_bots: int
    available_capacity: int
    healthy_workers: int
    total_workers: int


class BotAssignmentResponse(BaseModel):
    """Bot assignment info."""

    bot_id: str
    bot_type: str


class WorkerBotsResponse(BaseModel):
    """Bots assigned to a worker."""

    worker_id: str
    bots: list[BotAssignmentResponse]
    bot_count: int


class BotStatusResponse(BaseModel):
    """Bot deployment status response."""

    bot_id: str
    is_deployed: bool
    assigned_worker: str | None
    bot_type: str | None
    worker_healthy: bool | None = None


class BotActionResponse(BaseModel):
    """Bot action (activate/deactivate) response."""

    success: bool
    bot_id: str
    bot_type: str | None = None
    assigned_worker: str | None = None
    error: str | None = None


# ==================== Endpoints ====================


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    current_account: Account = Depends(get_current_account),
) -> WorkerListResponse:
    """List all registered bot workers.

    Returns information about all workers including health status and utilization.
    """
    redis_client = get_redis()
    registry = WorkerRegistry(redis_client)

    workers = registry.get_all_workers()
    healthy_count = sum(1 for w in workers if w.is_healthy)

    return WorkerListResponse(
        workers=[WorkerStatusResponse(**w.to_dict()) for w in workers],
        total_workers=len(workers),
        healthy_workers=healthy_count,
    )


@router.get("/capacity", response_model=CapacityResponse)
async def get_capacity(
    current_account: Account = Depends(get_current_account),
) -> CapacityResponse:
    """Get total worker pool capacity.

    Returns aggregate capacity information across all healthy workers.
    """
    redis_client = get_redis()
    registry = WorkerRegistry(redis_client)

    capacity = registry.get_total_capacity()
    return CapacityResponse(**capacity)


@router.get("/{worker_id}", response_model=WorkerStatusResponse)
async def get_worker(
    worker_id: str,
    current_account: Account = Depends(get_current_account),
) -> WorkerStatusResponse:
    """Get status of a specific worker.

    Args:
        worker_id: Worker ID to look up
    """
    redis_client = get_redis()
    registry = WorkerRegistry(redis_client)

    worker = registry.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    return WorkerStatusResponse(**worker.to_dict())


@router.get("/{worker_id}/bots", response_model=WorkerBotsResponse)
async def get_worker_bots(
    worker_id: str,
    current_account: Account = Depends(get_current_account),
) -> WorkerBotsResponse:
    """Get all bots assigned to a specific worker.

    Args:
        worker_id: Worker ID to look up
    """
    redis_client = get_redis()
    registry = WorkerRegistry(redis_client)

    bots = registry.get_bots_for_worker(worker_id)
    return WorkerBotsResponse(
        worker_id=worker_id,
        bots=[BotAssignmentResponse(**b) for b in bots],
        bot_count=len(bots),
    )


@router.post("/cleanup", response_model=dict[str, Any])
async def cleanup_dead_workers(
    current_account: Account = Depends(get_current_account),
) -> dict[str, Any]:
    """Remove dead workers from the registry.

    This triggers redistribution of their bots to healthy workers.
    """
    redis_client = get_redis()
    registry = WorkerRegistry(redis_client)

    removed = registry.cleanup_dead_workers()
    return {
        "success": True,
        "removed_workers": removed,
        "removed_count": len(removed),
    }


# ==================== Bot Deployment Endpoints ====================


@router.get("/bots/{bot_id}/status", response_model=BotStatusResponse)
async def get_bot_deployment_status(
    bot_id: str,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotStatusResponse:
    """Get deployment status of a specific bot.

    Args:
        bot_id: Bot ID to check
    """
    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    status = service.get_bot_status(bot_id)
    return BotStatusResponse(**status)


@router.post("/slack/{bot_id}/activate", response_model=BotActionResponse)
async def activate_slack_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Activate a Slack bot on the worker pool.

    Args:
        bot_id: Slack bot UUID to activate
    """
    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = await service.activate_slack_bot(bot_id)
    return BotActionResponse(**result)


@router.post("/slack/{bot_id}/deactivate", response_model=BotActionResponse)
async def deactivate_slack_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Deactivate a Slack bot on the worker pool.

    Args:
        bot_id: Slack bot UUID to deactivate
    """
    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = await service.deactivate_slack_bot(bot_id)
    return BotActionResponse(**result)


@router.post("/telegram/{bot_id}/activate", response_model=BotActionResponse)
async def activate_telegram_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Activate a Telegram bot on the worker pool.

    Args:
        bot_id: Telegram bot UUID to activate
    """
    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = await service.activate_telegram_bot(bot_id)
    return BotActionResponse(**result)


@router.post("/telegram/{bot_id}/deactivate", response_model=BotActionResponse)
async def deactivate_telegram_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Deactivate a Telegram bot on the worker pool.

    Args:
        bot_id: Telegram bot UUID to deactivate
    """
    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = await service.deactivate_telegram_bot(bot_id)
    return BotActionResponse(**result)


@router.post("/slack/{bot_id}/restart", response_model=BotActionResponse)
async def restart_slack_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Restart a Slack bot on the worker pool.

    Args:
        bot_id: Slack bot UUID to restart
    """
    from ..bot_worker.redis_state import BotType

    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = service.restart_bot(str(bot_id), BotType.SLACK)
    return BotActionResponse(**result)


@router.post("/telegram/{bot_id}/restart", response_model=BotActionResponse)
async def restart_telegram_bot(
    bot_id: UUID,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
) -> BotActionResponse:
    """Restart a Telegram bot on the worker pool.

    Args:
        bot_id: Telegram bot UUID to restart
    """
    from ..bot_worker.redis_state import BotType

    redis_client = get_redis()
    service = BotDeploymentService(db, redis_client)

    result = service.restart_bot(str(bot_id), BotType.TELEGRAM)
    return BotActionResponse(**result)
