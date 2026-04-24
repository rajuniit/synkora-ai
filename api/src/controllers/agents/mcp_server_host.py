"""
MCP Streamable HTTP server host controller.

Exposes each Synkora agent as an MCP server endpoint following the
MCP Streamable HTTP spec (2025-06-18). MCP clients such as the Claude Code
CLI can connect to this endpoint and call the agent as a tool.

Auth: AgentApiKey with 'mcp_server' permission (or none if agent is public-MCP).
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.agent_api_auth import AgentApiAuthMiddleware
from src.models.agent import Agent
from src.services.agents.mcp_server_host_service import MCPServerHostService

logger = logging.getLogger(__name__)

mcp_host_router = APIRouter()
_mcp_service = MCPServerHostService()

MCP_PROTOCOL_VERSION = "2025-06-18"


async def _get_agent(agent_id: str, db: AsyncSession) -> Agent:
    """Resolve and validate agent by ID."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID")

    result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def _check_mcp_enabled(agent: Agent) -> None:
    """Verify MCP server is enabled for this agent."""
    metadata = agent.agent_metadata or {}
    integrations = metadata.get("integrations_config", {})
    if not integrations.get("mcp_server_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MCP server is not enabled for this agent",
        )


async def _authenticate(request: Request, agent: Agent, db: AsyncSession) -> None:
    """
    Authenticate the MCP request.

    Skips auth if agent has mcp_server_public=true in metadata.
    Otherwise requires Bearer AgentApiKey with 'mcp_server' permission.
    """
    metadata = agent.agent_metadata or {}
    integrations = metadata.get("integrations_config", {})
    if integrations.get("mcp_server_public", False):
        return  # Public MCP endpoint

    # Re-use existing auth middleware
    await AgentApiAuthMiddleware.authenticate_request(request, required_permission="mcp_server")


@mcp_host_router.post("/{agent_id}")
async def mcp_post(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Main MCP JSON-RPC endpoint.

    Handles initialize, tools/list, tools/call (and ping).

    If the client sends Accept: text/event-stream for tools/call,
    responses are streamed as SSE.
    """
    agent = await _get_agent(agent_id, db)
    await _check_mcp_enabled(agent)
    await _authenticate(request, agent, db)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    accept = request.headers.get("Accept", "")
    method = payload.get("method", "")

    # SSE streaming path for tools/call
    if method == "tools/call" and "text/event-stream" in accept:
        params = payload.get("params", {})

        async def event_generator():
            async for chunk in _mcp_service.stream_tools_call(agent, params, db):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    # Standard JSON-RPC response
    result = await _mcp_service.handle_request(agent, payload, db)
    return result


@mcp_host_router.get("/{agent_id}")
async def mcp_get(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    SSE listening endpoint for server-initiated messages.

    Per spec, a GET opens an SSE channel. For now we return an open SSE
    connection that immediately sends a capabilities ping. Clients that need
    live server-push can keep this open; we do not currently use it for push.
    """
    agent = await _get_agent(agent_id, db)
    await _check_mcp_enabled(agent)
    await _authenticate(request, agent, db)

    import json

    async def ping_stream():
        import asyncio

        ping = {
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {"serverInfo": {"name": "synkora-agent", "version": "1.0.0"}},
        }
        yield f"data: {json.dumps(ping)}\n\n"
        # Keep-alive — clients close when done
        while True:
            await asyncio.sleep(30)
            yield ": keep-alive\n\n"

    return StreamingResponse(
        ping_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        },
    )


@mcp_host_router.delete("/{agent_id}")
async def mcp_delete(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """Terminate an MCP session (stateless — just 204)."""
    agent = await _get_agent(agent_id, db)
    await _check_mcp_enabled(agent)
    await _authenticate(request, agent, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
