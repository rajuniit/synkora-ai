"""
Execution Registry — Redis-based tracking of all agent executions across trigger sources.

Provides a centralized view of all running and recently completed agent executions
for the Live Lab observation dashboard.
"""

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.config.redis import get_redis_async

logger = logging.getLogger(__name__)

# Redis key patterns
_EXEC_KEY = "exec:{tenant_id}:{execution_id}"
_ACTIVE_SET = "exec:active:{tenant_id}"
_RECENT_LIST = "exec:recent:{tenant_id}"
_EVENTS_KEY = "exec:events:{execution_id}"

# TTLs
_EXEC_TTL = 86400  # 24 hours
_EVENTS_TTL = 86400  # 24 hours
_RECENT_MAX = 200  # Max recent executions to keep


class ExecutionRegistry:
    """Tracks agent executions in Redis for real-time observability."""

    @staticmethod
    async def register(
        tenant_id: str | UUID,
        agent_id: str | UUID,
        agent_name: str,
        trigger_source: str,
        conversation_id: str | UUID | None = None,
        trigger_detail: str | None = None,
        message_preview: str | None = None,
        execution_id: str | None = None,
    ) -> str:
        """
        Register a new agent execution.

        Args:
            tenant_id: Tenant owning this execution
            agent_id: The agent being executed
            agent_name: Display name of the agent
            trigger_source: Where the execution was triggered from
                (chat, slack, whatsapp, telegram, teams, widget, scheduler, api)
            conversation_id: Optional conversation ID
            trigger_detail: Extra context (e.g., "#general", "+1234567890")
            message_preview: First ~100 chars of the user message
            execution_id: Optional pre-generated execution ID

        Returns:
            execution_id (str)
        """
        redis = get_redis_async()
        tid = str(tenant_id)
        eid = execution_id or str(uuid4())

        data = {
            "id": eid,
            "agent_id": str(agent_id),
            "agent_name": agent_name,
            "trigger_source": trigger_source,
            "trigger_detail": trigger_detail or "",
            "message_preview": (message_preview or "")[:200],
            "conversation_id": str(conversation_id) if conversation_id else "",
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": "",
            "error": "",
            "tools_used": "[]",
            "total_tokens": "0",
            "total_tools": "0",
            "cost": "0",
        }

        key = _EXEC_KEY.format(tenant_id=tid, execution_id=eid)
        pipe = redis.pipeline()
        pipe.hset(key, mapping=data)
        pipe.expire(key, _EXEC_TTL)
        pipe.sadd(_ACTIVE_SET.format(tenant_id=tid), eid)
        await pipe.execute()

        logger.info(f"Execution registered: {eid} for agent {agent_name} via {trigger_source}")
        return eid

    @staticmethod
    async def update_status(
        tenant_id: str | UUID,
        execution_id: str,
        status: str,
        error: str | None = None,
        total_tokens: int | None = None,
        cost: float | None = None,
    ) -> None:
        """Update execution status (complete, error, etc.)."""
        redis = get_redis_async()
        tid = str(tenant_id)
        key = _EXEC_KEY.format(tenant_id=tid, execution_id=execution_id)

        updates: dict[str, str] = {"status": status}
        if status in ("complete", "error", "cancelled"):
            updates["completed_at"] = datetime.now(UTC).isoformat()
        if error:
            updates["error"] = error[:500]
        if total_tokens is not None:
            updates["total_tokens"] = str(total_tokens)
        if cost is not None:
            updates["cost"] = str(cost)

        pipe = redis.pipeline()
        pipe.hset(key, mapping=updates)

        if status in ("complete", "error", "cancelled"):
            active_key = _ACTIVE_SET.format(tenant_id=tid)
            recent_key = _RECENT_LIST.format(tenant_id=tid)
            pipe.srem(active_key, execution_id)
            pipe.lpush(recent_key, execution_id)
            pipe.ltrim(recent_key, 0, _RECENT_MAX - 1)
            pipe.expire(recent_key, _EXEC_TTL)

        await pipe.execute()

    @staticmethod
    async def record_tool(
        tenant_id: str | UUID,
        execution_id: str,
        tool_name: str,
    ) -> None:
        """Record a tool being used in an execution."""
        redis = get_redis_async()
        tid = str(tenant_id)
        key = _EXEC_KEY.format(tenant_id=tid, execution_id=execution_id)

        raw = await redis.hget(key, "tools_used")
        tools: list[str] = json.loads(raw) if raw else []
        if tool_name not in tools:
            tools.append(tool_name)

        pipe = redis.pipeline()
        pipe.hset(key, mapping={
            "tools_used": json.dumps(tools),
            "total_tools": str(len(tools)),
        })
        await pipe.execute()

    @staticmethod
    async def append_event(
        execution_id: str,
        event: dict[str, Any],
    ) -> None:
        """Append an SSE event to the execution's event log for replay."""
        redis = get_redis_async()
        events_key = _EVENTS_KEY.format(execution_id=execution_id)

        entry = {**event, "_ts": time.time()}
        pipe = redis.pipeline()
        pipe.rpush(events_key, json.dumps(entry))
        pipe.expire(events_key, _EVENTS_TTL)
        await pipe.execute()

    @staticmethod
    async def get_events(execution_id: str) -> list[dict[str, Any]]:
        """Get all events for an execution (for replay)."""
        redis = get_redis_async()
        events_key = _EVENTS_KEY.format(execution_id=execution_id)
        raw_events = await redis.lrange(events_key, 0, -1)
        return [json.loads(e) for e in raw_events]

    @staticmethod
    async def get_execution(
        tenant_id: str | UUID,
        execution_id: str,
    ) -> dict[str, Any] | None:
        """Get execution details."""
        redis = get_redis_async()
        tid = str(tenant_id)
        key = _EXEC_KEY.format(tenant_id=tid, execution_id=execution_id)
        data = await redis.hgetall(key)
        if not data:
            return None
        data["tools_used"] = json.loads(data.get("tools_used", "[]"))
        data["total_tokens"] = int(data.get("total_tokens", 0))
        data["total_tools"] = int(data.get("total_tools", 0))
        data["cost"] = float(data.get("cost", 0))
        return data

    @staticmethod
    async def list_active(tenant_id: str | UUID) -> list[dict[str, Any]]:
        """List all active (running) executions for a tenant."""
        redis = get_redis_async()
        tid = str(tenant_id)
        active_ids = await redis.smembers(_ACTIVE_SET.format(tenant_id=tid))

        if not active_ids:
            return []

        pipe = redis.pipeline()
        for eid in active_ids:
            pipe.hgetall(_EXEC_KEY.format(tenant_id=tid, execution_id=eid))
        results = await pipe.execute()

        executions = []
        for data in results:
            if data and data.get("id"):
                data["tools_used"] = json.loads(data.get("tools_used", "[]"))
                data["total_tokens"] = int(data.get("total_tokens", 0))
                data["total_tools"] = int(data.get("total_tools", 0))
                data["cost"] = float(data.get("cost", 0))
                executions.append(data)

        executions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return executions

    @staticmethod
    async def list_recent(
        tenant_id: str | UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List recently completed executions."""
        redis = get_redis_async()
        tid = str(tenant_id)
        recent_key = _RECENT_LIST.format(tenant_id=tid)
        recent_ids = await redis.lrange(recent_key, offset, offset + limit - 1)

        if not recent_ids:
            return []

        pipe = redis.pipeline()
        for eid in recent_ids:
            pipe.hgetall(_EXEC_KEY.format(tenant_id=tid, execution_id=eid))
        results = await pipe.execute()

        executions = []
        for data in results:
            if data and data.get("id"):
                data["tools_used"] = json.loads(data.get("tools_used", "[]"))
                data["total_tokens"] = int(data.get("total_tokens", 0))
                data["total_tools"] = int(data.get("total_tools", 0))
                data["cost"] = float(data.get("cost", 0))
                executions.append(data)

        return executions


# Module-level singleton
execution_registry = ExecutionRegistry()
