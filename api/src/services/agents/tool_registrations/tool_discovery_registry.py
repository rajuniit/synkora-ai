"""
Tool Discovery Registry

Registers the tool discovery meta-tool that allows LLM to search for
additional tools on-demand.

This tool should ALWAYS be included in the tool list sent to LLM,
providing a safety net when initial filtering might miss relevant tools.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# This tool name should always be included in filtered tool lists
ALWAYS_INCLUDE_TOOLS = [
    "internal_search_available_tools",
    "internal_list_tool_categories",
]


def register_tool_discovery_tools(registry):
    """
    Register tool discovery tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.tool_discovery_tools import (
        internal_list_tool_categories,
        internal_search_available_tools,
    )

    # Wrapper for search_available_tools
    async def internal_search_available_tools_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_search_available_tools(
            query=kwargs.get("query", ""),
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    # Wrapper for list_tool_categories
    async def internal_list_tool_categories_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_list_tool_categories(
            runtime_context=runtime_context,
            config=config,
        )

    # Register search_available_tools
    registry.register_tool(
        name="internal_search_available_tools",
        description=(
            "IMPORTANT: Before telling the user you cannot do something, ALWAYS use this tool first "
            "to search for capabilities you might be missing. "
            "Describe what you need (e.g., 'schedule daily tasks at specific time', 'send email notifications', "
            "'youtube transcripts', 'slack messaging') and this will return matching tools you can use. "
            "Many capabilities like email, scheduling, messaging, and integrations are available but may not "
            "be in your initial tool set. Search before saying you can't do something."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Description of the capability you need (e.g., 'schedule daily tasks', 'search youtube')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tools to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        function=internal_search_available_tools_wrapper,
    )

    # Register list_tool_categories
    registry.register_tool(
        name="internal_list_tool_categories",
        description=(
            "List available tool categories to understand what capabilities exist. "
            "Use this to explore available integrations before searching for specific tools."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_list_tool_categories_wrapper,
    )

    logger.info("Registered 2 tool discovery tools (always included)")
