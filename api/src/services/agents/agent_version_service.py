"""Agent versioning service."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.agent_version import AgentVersion

logger = logging.getLogger(__name__)

# Fields to capture in snapshot (exclude system fields)
SNAPSHOT_FIELDS = [
    "agent_name",
    "description",
    "system_prompt",
    "llm_config",
    "tools_config",
    "observability_config",
    "suggestion_prompts",
    "voice_enabled",
    "voice_config",
    "is_public",
    "avatar",
    "category",
    "tags",
    "workflow_type",
    "workflow_config",
    "routing_mode",
    "routing_config",
    "execution_backend",
    "agent_metadata",
]


async def create_version(
    db: AsyncSession,
    agent: Agent,
    account_id,
    change_description: str | None = None,
) -> AgentVersion:
    """Snapshot the current agent state as a new version."""
    # Get next version number for this agent
    result = await db.execute(select(func.max(AgentVersion.version_number)).filter(AgentVersion.agent_id == agent.id))
    max_version = result.scalar() or 0
    next_version = max_version + 1

    # Build snapshot from agent fields that exist
    snapshot = {}
    for field in SNAPSHOT_FIELDS:
        val = getattr(agent, field, None)
        if val is not None:
            # Convert UUID and non-serializable types to str
            snapshot[field] = str(val) if hasattr(val, "hex") else val

    version = AgentVersion(
        agent_id=agent.id,
        tenant_id=agent.tenant_id,
        created_by=account_id,
        version_number=next_version,
        change_description=change_description,
        snapshot=snapshot,
    )
    db.add(version)
    return version


async def list_versions(
    db: AsyncSession,
    agent_id,
    tenant_id,
    limit: int = 50,
) -> list[AgentVersion]:
    """List versions for an agent, newest first."""
    result = await db.execute(
        select(AgentVersion)
        .filter(AgentVersion.agent_id == agent_id, AgentVersion.tenant_id == tenant_id)
        .order_by(AgentVersion.version_number.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def restore_version(
    db: AsyncSession,
    agent: Agent,
    version: AgentVersion,
    account_id,
) -> AgentVersion:
    """Restore agent to a previous version snapshot, creating a new version entry."""
    snapshot = version.snapshot or {}
    for field, value in snapshot.items():
        if hasattr(agent, field):
            setattr(agent, field, value)

    # Record the restore as a new version
    return await create_version(
        db,
        agent,
        account_id,
        change_description=f"Restored to version {version.version_number}",
    )
