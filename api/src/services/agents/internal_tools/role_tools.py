"""
Role Tools for Role-Based Agents.

Internal tools for agents with roles to access project context,
escalate to humans, and collaborate with other agents.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

logger = logging.getLogger(__name__)


async def internal_get_project_info(
    project_id: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get basic information about a project.

    Use this to understand the project you're working on, including its name,
    description, status, and external tool references.

    Args:
        project_id: The project ID to get information for
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with project information including name, description, status,
        and external project references (Jira, ClickUp, GitHub)
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.project_service import ProjectService

        async for db in get_async_db():
            service = ProjectService(db)

            project = await service.get_project(UUID(project_id))
            if not project:
                return {"error": f"Project not found: {project_id}"}

            return {
                "success": True,
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "external_refs": project.external_project_ref or {},
                    "has_knowledge_base": project.knowledge_base_id is not None,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                },
            }
    except Exception as e:
        logger.error(f"Error getting project info: {e}")
        return {"error": str(e)}


async def internal_get_project_context(
    project_id: str,
    key: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get shared context for a project.

    Shared context is real-time state that all agents on the project can read
    and write to. Use this to coordinate with other agents or maintain
    project-level state.

    Args:
        project_id: The project ID
        key: Optional specific key to retrieve. If not provided, returns all context.
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with shared context data
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.project_service import ProjectService

        async for db in get_async_db():
            service = ProjectService(db)

            context = await service.get_context(UUID(project_id))
            if context is None:
                return {"error": f"Project not found: {project_id}"}

            if key:
                value = context.get(key)
                return {"success": True, "key": key, "value": value, "found": key in context}

            return {"success": True, "context": context}
    except Exception as e:
        logger.error(f"Error getting project context: {e}")
        return {"error": str(e)}


async def internal_update_project_context(
    project_id: str,
    key: str,
    value: Any,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Update shared context for a project.

    Add or update a key-value pair in the project's shared context.
    Other agents on the project can read this value.

    Args:
        project_id: The project ID
        key: The context key to set
        value: The value to store (can be string, number, boolean, list, or dict)
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary indicating success or failure
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.project_service import ProjectService

        async for db in get_async_db():
            service = ProjectService(db)

            # Get tenant_id from runtime context or project
            project = await service.get_project(UUID(project_id))
            if not project:
                return {"error": f"Project not found: {project_id}"}

            result = await service.set_context_value(
                project_id=UUID(project_id), tenant_id=project.tenant_id, key=key, value=value
            )

            if not result:
                return {"error": "Failed to update context"}

            return {"success": True, "message": f"Context key '{key}' updated successfully"}
    except Exception as e:
        logger.error(f"Error updating project context: {e}")
        return {"error": str(e)}


async def internal_escalate_to_human(
    reason: str,
    subject: str,
    message: str,
    priority: str = "medium",
    context_summary: str | None = None,
    runtime_context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Escalate a matter to your linked human contact.

    Use this when you need human input, approval, or when facing situations
    beyond your capabilities. Your human will be notified via their preferred
    channel (Slack, WhatsApp, or Email).

    Valid reasons:
    - uncertainty: You're uncertain about a decision
    - approval_needed: Action requires human approval
    - complex_decision: Complex decision requiring human judgment
    - blocker: You've hit a blocker that needs human intervention
    - review_required: Work needs human review before proceeding
    - customer_request: Customer specifically requested human contact
    - security_concern: Potential security issue identified
    - budget_approval: Budget-related decision needed

    Valid priorities:
    - low: Not urgent, can wait
    - medium: Normal priority, respond when convenient
    - high: Important, please respond soon
    - urgent: Critical, immediate attention required

    Args:
        reason: The reason for escalation (see valid reasons above)
        subject: Brief subject line (max 100 chars)
        message: Detailed message explaining the situation
        priority: Urgency level (default: medium)
        context_summary: Optional summary of conversation context
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with escalation status and ID
    """
    try:
        from src.core.database import get_async_db
        from src.models import Agent, ProjectAgent
        from src.services.roles.human_escalation_service import HumanEscalationService

        if not runtime_context:
            return {"error": "Runtime context required for escalation"}

        agent_id = runtime_context.get("agent_id")
        conversation_id = runtime_context.get("conversation_id")

        if not agent_id:
            return {"error": "Agent ID not found in runtime context"}

        async for db in get_async_db():
            # Get the agent
            result = await db.execute(select(Agent).filter(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                return {"error": "Agent not found"}

            if not agent.human_contact_id:
                return {"error": "No human contact linked to this agent. Cannot escalate."}

            # Find project for this agent
            result = await db.execute(select(ProjectAgent).filter(ProjectAgent.agent_id == agent_id))
            project_agent = result.scalar_one_or_none()

            if not project_agent:
                return {"error": "Agent is not assigned to any project. Cannot escalate."}

            # Create escalation
            service = HumanEscalationService(db)

            escalation = await service.create_escalation(
                tenant_id=agent.tenant_id,
                project_id=project_agent.project_id,
                from_agent_id=agent_id,
                to_human_id=agent.human_contact_id,
                reason=reason,
                subject=subject[:100],  # Truncate to 100 chars
                message=message,
                context_summary=context_summary,
                priority=priority,
                conversation_id=UUID(conversation_id) if conversation_id else None,
                auto_notify=True,
            )

            human = escalation.to_human

            return {
                "success": True,
                "escalation_id": str(escalation.id),
                "status": escalation.status,
                "notified_human": human.name if human else None,
                "notification_channels": escalation.notification_channels,
                "message": f"Escalation created and {human.name if human else 'human'} has been notified.",
            }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error creating escalation: {e}")
        return {"error": str(e)}


async def internal_get_my_human_contact(
    runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get information about your linked human contact.

    Returns details about the human you can escalate to, including their
    name and preferred contact method.

    Args:
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with human contact information
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.human_contact_service import HumanContactService

        if not runtime_context:
            return {"error": "Runtime context required"}

        agent_id = runtime_context.get("agent_id")
        if not agent_id:
            return {"error": "Agent ID not found in runtime context"}

        async for db in get_async_db():
            service = HumanContactService(db)

            human = await service.get_contact_for_agent(UUID(agent_id))
            if not human:
                return {"success": False, "error": "No human contact linked to this agent"}

            return {
                "success": True,
                "human": {
                    "id": str(human.id),
                    "name": human.name,
                    "preferred_channel": human.preferred_channel,
                    "available_channels": human.get_available_channels(),
                    "is_active": human.is_active,
                    "timezone": human.timezone,
                },
            }
    except Exception as e:
        logger.error(f"Error getting human contact: {e}")
        return {"error": str(e)}


async def internal_check_escalation_status(
    escalation_id: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Check the status of an escalation.

    Use this to see if your human has responded to an escalation
    you previously created.

    Args:
        escalation_id: The escalation ID to check
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with escalation status and human response if available
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.human_escalation_service import HumanEscalationService

        async for db in get_async_db():
            service = HumanEscalationService(db)

            escalation = await service.get_escalation(UUID(escalation_id))
            if not escalation:
                return {"error": f"Escalation not found: {escalation_id}"}

            result = {
                "success": True,
                "escalation_id": str(escalation.id),
                "status": escalation.status,
                "subject": escalation.subject,
                "reason": escalation.reason,
                "priority": escalation.priority,
                "created_at": escalation.created_at.isoformat() if escalation.created_at else None,
                "is_resolved": escalation.is_resolved,
                "is_pending": escalation.is_pending,
            }

            if escalation.human_response:
                result["human_response"] = escalation.human_response
                result["resolved_at"] = escalation.resolved_at.isoformat() if escalation.resolved_at else None

            if escalation.notification_sent_at:
                result["notification_sent_at"] = escalation.notification_sent_at.isoformat()

            return result
    except Exception as e:
        logger.error(f"Error checking escalation status: {e}")
        return {"error": str(e)}


async def internal_get_project_agents(
    project_id: str, runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    List other agents assigned to the same project.

    Use this to understand who else is working on the project
    and their roles.

    Args:
        project_id: The project ID
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with list of agents on the project
    """
    try:
        from src.core.database import get_async_db
        from src.services.roles.project_service import ProjectService

        async for db in get_async_db():
            service = ProjectService(db)

            agents = await service.get_project_agents(UUID(project_id))

            current_agent_id = None
            if runtime_context:
                current_agent_id = runtime_context.get("agent_id")

            return {
                "success": True,
                "project_id": project_id,
                "agents": [
                    {
                        "id": str(agent.id),
                        "name": agent.agent_name,
                        "type": agent.agent_type,
                        "role_type": agent.role.role_type if agent.role else None,
                        "role_name": agent.role.role_name if agent.role else None,
                        "has_human_contact": agent.human_contact_id is not None,
                        "is_current": str(agent.id) == str(current_agent_id) if current_agent_id else False,
                    }
                    for agent in agents
                ],
                "total_agents": len(agents),
            }
    except Exception as e:
        logger.error(f"Error getting project agents: {e}")
        return {"error": str(e)}


async def internal_get_my_role(
    runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get information about your assigned role.

    Returns details about your role including type, name, and
    suggested tools for your role.

    Args:
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with role information
    """
    try:
        from src.core.database import get_async_db
        from src.models import Agent

        if not runtime_context:
            return {"error": "Runtime context required"}

        agent_id = runtime_context.get("agent_id")
        if not agent_id:
            return {"error": "Agent ID not found in runtime context"}

        async for db in get_async_db():
            result = await db.execute(select(Agent).filter(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                return {"error": "Agent not found"}

            if not agent.role:
                return {"success": False, "error": "No role assigned to this agent"}

            role = agent.role

            return {
                "success": True,
                "role": {
                    "id": str(role.id),
                    "type": role.role_type,
                    "name": role.role_name,
                    "description": role.description,
                    "suggested_tools": role.suggested_tools or [],
                    "capabilities": role.default_capabilities or {},
                },
            }
    except Exception as e:
        logger.error(f"Error getting role: {e}")
        return {"error": str(e)}


async def internal_get_pending_escalations(
    runtime_context: dict[str, Any] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get your pending escalations that haven't been resolved.

    Use this to check if there are any outstanding escalations
    you've created that are awaiting human response.

    Args:
        runtime_context: Runtime context from agent execution
        config: Config dict

    Returns:
        Dictionary with list of pending escalations
    """
    try:
        from datetime import UTC, datetime

        from sqlalchemy import and_, or_

        from src.core.database import get_async_db
        from src.models import EscalationStatus, HumanEscalation

        if not runtime_context:
            return {"error": "Runtime context required"}

        agent_id = runtime_context.get("agent_id")
        if not agent_id:
            return {"error": "Agent ID not found in runtime context"}

        async for db in get_async_db():
            # Get pending escalations from this agent
            result = await db.execute(
                select(HumanEscalation)
                .filter(
                    and_(
                        HumanEscalation.from_agent_id == agent_id,
                        HumanEscalation.status.in_(
                            [
                                EscalationStatus.PENDING.value,
                                EscalationStatus.NOTIFIED.value,
                                EscalationStatus.IN_PROGRESS.value,
                            ]
                        ),
                        or_(HumanEscalation.expires_at is None, HumanEscalation.expires_at > datetime.now(UTC)),
                    )
                )
                .order_by(HumanEscalation.created_at.desc())
            )
            escalations = list(result.scalars().all())

            return {
                "success": True,
                "pending_count": len(escalations),
                "escalations": [
                    {
                        "id": str(e.id),
                        "subject": e.subject,
                        "reason": e.reason,
                        "priority": e.priority,
                        "status": e.status,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                        "to_human": e.to_human.name if e.to_human else None,
                    }
                    for e in escalations
                ],
            }
    except Exception as e:
        logger.error(f"Error getting pending escalations: {e}")
        return {"error": str(e)}
