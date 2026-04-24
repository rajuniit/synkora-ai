"""
Google A2A Protocol controller.

Exposes Synkora agents via the A2A JSON-RPC API:
  - GET  /api/a2a/agents/{agent_id}/.well-known/agent.json  → Agent Card
  - GET  /api/a2a/.well-known/agents                        → Public agent directory
  - POST /api/a2a/agents/{agent_id}                         → JSON-RPC dispatcher

Supported JSON-RPC methods:
  message/send        — synchronous invocation
  tasks/send          — async (Celery-backed) task
  tasks/get           — poll task status
  tasks/cancel        — cancel task
  tasks/sendSubscribe — async + SSE streaming
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.agent_api_auth import AgentApiAuthMiddleware
from src.models.agent import Agent
from src.models.agent_a2a_task import A2ATaskStatus, AgentA2ATask
from src.services.agents.a2a_service import A2AService, _task_to_dict
from src.utils.config_helper import get_app_base_url

logger = logging.getLogger(__name__)

a2a_router = APIRouter()
_a2a_service = A2AService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_agent(agent_id: str, db: AsyncSession) -> Agent:
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID")

    result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def _check_a2a_enabled(agent: Agent) -> None:
    metadata = agent.agent_metadata or {}
    integrations = metadata.get("integrations_config", {})
    if not integrations.get("a2a_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A2A protocol is not enabled for this agent",
        )


async def _authenticate_a2a(request: Request, agent: Agent) -> None:
    """Require Bearer AgentApiKey with 'a2a' permission."""
    await AgentApiAuthMiddleware.authenticate_request(request, required_permission="a2a")


def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _jsonrpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


# ---------------------------------------------------------------------------
# Agent Card (public discovery)
# ---------------------------------------------------------------------------


@a2a_router.get("/agents/{agent_id}/.well-known/agent.json")
async def get_agent_card(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Return the Agent Card for discovery.

    If a2a_public=true the card is accessible without auth.
    Otherwise Bearer token with 'a2a' permission is required.
    """
    agent = await _get_agent(agent_id, db)
    await _check_a2a_enabled(agent)

    metadata = agent.agent_metadata or {}
    integrations = metadata.get("integrations_config", {})
    if not integrations.get("a2a_public", False):
        await _authenticate_a2a(request, agent)

    base_url = await get_app_base_url(db, agent.tenant_id)
    return _a2a_service.get_agent_card(agent, base_url)


@a2a_router.get("/.well-known/agents")
async def list_public_agents(db: AsyncSession = Depends(get_async_db)) -> dict:
    """Return a directory of all agents with A2A and a2a_public=true."""
    result = await db.execute(select(Agent).where(Agent.status == "ACTIVE"))
    agents = result.scalars().all()

    public_agents = []
    for agent in agents:
        metadata = agent.agent_metadata or {}
        integrations = metadata.get("integrations_config", {})
        if integrations.get("a2a_enabled") and integrations.get("a2a_public"):
            public_agents.append(
                {
                    "id": str(agent.id),
                    "name": agent.agent_name,
                    "description": agent.description or "",
                }
            )

    return {"agents": public_agents}


# ---------------------------------------------------------------------------
# JSON-RPC dispatcher
# ---------------------------------------------------------------------------


@a2a_router.post("/agents/{agent_id}")
async def a2a_dispatch(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Dispatch an A2A JSON-RPC request for the given agent.
    """
    agent = await _get_agent(agent_id, db)
    await _check_a2a_enabled(agent)
    await _authenticate_a2a(request, agent)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    method = payload.get("method")
    req_id = payload.get("id")
    params = payload.get("params", {})

    if method == "message/send":
        return await _handle_message_send(req_id, params, agent, db)
    elif method == "tasks/send":
        return await _handle_tasks_send(req_id, params, agent, request, db)
    elif method == "tasks/get":
        return await _handle_tasks_get(req_id, params, agent, db)
    elif method == "tasks/cancel":
        return await _handle_tasks_cancel(req_id, params, agent, db)
    elif method == "tasks/sendSubscribe":
        return await _handle_tasks_send_subscribe(req_id, params, agent, request, db)
    else:
        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Method handlers
# ---------------------------------------------------------------------------


async def _handle_message_send(req_id: Any, params: dict, agent: Agent, db: AsyncSession) -> dict:
    """Synchronous: run agent and return completed task."""
    result = await _a2a_service.send_message(agent, params, db)
    return _jsonrpc_result(req_id, result)


async def _handle_tasks_send(req_id: Any, params: dict, agent: Agent, request: Request, db: AsyncSession) -> dict:
    """Async: create task and return immediately (status=submitted)."""
    caller_info = {"ip": request.client.host if request.client else None}
    task = await _a2a_service.create_task(agent, params, caller_info, db)
    return _jsonrpc_result(req_id, _task_to_dict(task))


async def _handle_tasks_get(req_id: Any, params: dict, agent: Agent, db: AsyncSession) -> dict:
    """Poll task status."""
    task_id = params.get("id")
    if not task_id:
        return _jsonrpc_error(req_id, -32602, "Parameter 'id' is required")

    task = await _a2a_service.get_task(str(agent.id), task_id, db)
    if not task:
        return _jsonrpc_error(req_id, -32602, f"Task {task_id} not found")

    return _jsonrpc_result(req_id, _task_to_dict(task))


async def _handle_tasks_cancel(req_id: Any, params: dict, agent: Agent, db: AsyncSession) -> dict:
    """Cancel a task."""
    task_id = params.get("id")
    if not task_id:
        return _jsonrpc_error(req_id, -32602, "Parameter 'id' is required")

    task = await _a2a_service.get_task(str(agent.id), task_id, db)
    if not task:
        return _jsonrpc_error(req_id, -32602, f"Task {task_id} not found")

    task = await _a2a_service.cancel_task(task, db)
    return _jsonrpc_result(req_id, _task_to_dict(task))


async def _handle_tasks_send_subscribe(
    req_id: Any,
    params: dict,
    agent: Agent,
    request: Request,
    db: AsyncSession,
) -> Any:
    """
    Create task + open SSE stream for live updates.

    Returns a StreamingResponse with A2A task events.
    """
    caller_info = {"ip": request.client.host if request.client else None}

    # Create task record (submitted status)
    task = await _a2a_service.create_task(agent, params, caller_info, db)

    async def event_generator():
        async for chunk in _a2a_service.stream_task(agent, task, db):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
