"""
Role Tools Registry

Registers role-based agent tools with the ADK tool registry.
These tools allow agents with roles to access project context,
escalate to humans, and collaborate with other agents.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_role_tools(registry):
    """
    Register all role-based agent tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.role_tools import (
        internal_check_escalation_status,
        internal_escalate_to_human,
        internal_get_my_human_contact,
        internal_get_my_role,
        internal_get_pending_escalations,
        internal_get_project_agents,
        internal_get_project_context,
        internal_get_project_info,
        internal_update_project_context,
    )

    # Wrapper functions that extract runtime_context from config

    async def get_project_info_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_project_info(
            project_id=kwargs.get("project_id"), runtime_context=runtime_context, config=config
        )

    async def get_project_context_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_project_context(
            project_id=kwargs.get("project_id"), key=kwargs.get("key"), runtime_context=runtime_context, config=config
        )

    async def update_project_context_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_update_project_context(
            project_id=kwargs.get("project_id"),
            key=kwargs.get("key"),
            value=kwargs.get("value"),
            runtime_context=runtime_context,
            config=config,
        )

    async def escalate_to_human_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_escalate_to_human(
            reason=kwargs.get("reason"),
            subject=kwargs.get("subject"),
            message=kwargs.get("message"),
            priority=kwargs.get("priority", "medium"),
            context_summary=kwargs.get("context_summary"),
            runtime_context=runtime_context,
            config=config,
        )

    async def get_my_human_contact_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_my_human_contact(runtime_context=runtime_context, config=config)

    async def check_escalation_status_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_check_escalation_status(
            escalation_id=kwargs.get("escalation_id"), runtime_context=runtime_context, config=config
        )

    async def get_project_agents_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_project_agents(
            project_id=kwargs.get("project_id"), runtime_context=runtime_context, config=config
        )

    async def get_my_role_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_my_role(runtime_context=runtime_context, config=config)

    async def get_pending_escalations_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_pending_escalations(runtime_context=runtime_context, config=config)

    # Register tools with the registry (following the same pattern as slack_tools_registry.py)

    registry.register_tool(
        name="get_project_info",
        description="Get basic information about a project including name, description, status, and external tool references (Jira, ClickUp, GitHub).",
        parameters={
            "type": "object",
            "properties": {"project_id": {"type": "string", "description": "The project ID to get information for"}},
            "required": ["project_id"],
        },
        function=get_project_info_wrapper,
    )

    registry.register_tool(
        name="get_project_context",
        description="Get shared context for a project. Shared context is real-time state that all agents on the project can read and write to.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "The project ID"},
                "key": {
                    "type": "string",
                    "description": "Optional specific key to retrieve. If not provided, returns all context.",
                },
            },
            "required": ["project_id"],
        },
        function=get_project_context_wrapper,
    )

    registry.register_tool(
        name="update_project_context",
        description="Update shared context for a project. Add or update a key-value pair that other agents on the project can read.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "The project ID"},
                "key": {"type": "string", "description": "The context key to set"},
                "value": {
                    "type": "string",
                    "description": "The value to store (can be string, number, boolean, list, or dict as JSON string)",
                },
            },
            "required": ["project_id", "key", "value"],
        },
        function=update_project_context_wrapper,
    )

    registry.register_tool(
        name="escalate_to_human",
        description="""Escalate a matter to your linked human contact. Use this when you need human input, approval, or face situations beyond your capabilities.

Valid reasons: uncertainty, approval_needed, complex_decision, blocker, review_required, customer_request, security_concern, budget_approval
Valid priorities: low, medium, high, urgent""",
        parameters={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for escalation (uncertainty, approval_needed, complex_decision, blocker, review_required, customer_request, security_concern, budget_approval)",
                },
                "subject": {"type": "string", "description": "Brief subject line (max 100 characters)"},
                "message": {"type": "string", "description": "Detailed message explaining the situation"},
                "priority": {
                    "type": "string",
                    "description": "Urgency level: low, medium, high, urgent (default: medium)",
                    "default": "medium",
                },
                "context_summary": {
                    "type": "string",
                    "description": "Optional summary of conversation context for the human",
                },
            },
            "required": ["reason", "subject", "message"],
        },
        function=escalate_to_human_wrapper,
    )

    registry.register_tool(
        name="get_my_human_contact",
        description="Get information about your linked human contact, including their name and preferred contact method.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=get_my_human_contact_wrapper,
    )

    registry.register_tool(
        name="check_escalation_status",
        description="Check the status of an escalation to see if your human has responded.",
        parameters={
            "type": "object",
            "properties": {"escalation_id": {"type": "string", "description": "The escalation ID to check"}},
            "required": ["escalation_id"],
        },
        function=check_escalation_status_wrapper,
    )

    registry.register_tool(
        name="get_project_agents",
        description="List other agents assigned to the same project, including their roles.",
        parameters={
            "type": "object",
            "properties": {"project_id": {"type": "string", "description": "The project ID"}},
            "required": ["project_id"],
        },
        function=get_project_agents_wrapper,
    )

    registry.register_tool(
        name="get_my_role",
        description="Get information about your assigned role including type, name, description, and suggested tools.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=get_my_role_wrapper,
    )

    registry.register_tool(
        name="get_pending_escalations",
        description="Get your pending escalations that haven't been resolved yet.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=get_pending_escalations_wrapper,
    )

    logger.info("Registered 9 role-based agent tools")
