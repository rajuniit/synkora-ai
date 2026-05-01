"""
Remote Agent Tools Registry

Registers the call_remote_agent tool so agents can delegate work to
external A2A or MCP endpoints.
"""

import logging

logger = logging.getLogger(__name__)


def register_remote_agent_tools(registry) -> None:
    """Register remote agent call tools with the ADK tool registry."""
    from src.services.agents.internal_tools.remote_agent_tool import call_remote_agent

    registry.register_tool(
        name="call_remote_agent",
        function=call_remote_agent,
        description=(
            "Call a REMOTE agent at an external URL via A2A or MCP protocol. "
            "SYNCHRONOUS — blocks until the remote agent replies and returns the full result immediately. "
            "No polling required. "
            "Use this to delegate work to a specific agent at a known endpoint URL "
            "(e.g. https://host/api/a2a/agents/{agent_id}). "
            "Do NOT use for local sub-tasks on the same server — use spawn_agent instead."
        ),
        parameters={
            "type": "object",
            "properties": {
                "endpoint_url": {
                    "type": "string",
                    "description": (
                        "Remote agent endpoint URL. "
                        "A2A: https://host/api/a2a/agents/{agent_id} — "
                        "MCP: https://host/api/mcp/{agent_id}"
                    ),
                },
                "message": {
                    "type": "string",
                    "description": "The message or task to send to the remote agent.",
                },
                "protocol": {
                    "type": "string",
                    "enum": ["a2a", "mcp"],
                    "description": "Protocol to use. Default: 'a2a'.",
                },
                "api_key": {
                    "type": "string",
                    "description": "Bearer API key for authenticating with the remote agent (if required).",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Optional conversation/context ID for multi-turn continuity.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Request timeout in seconds (max 300). Default: 60.",
                },
            },
            "required": ["endpoint_url", "message"],
        },
        tool_category="remote_agent",
    )
    logger.debug("[RemoteAgent] Registered call_remote_agent tool")
