"""
Elasticsearch Tools Registry

Registers all Elasticsearch-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_elasticsearch_tools(registry):
    """
    Register all Elasticsearch tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.elasticsearch_tools import (
        internal_elasticsearch_get_index_stats,
        internal_elasticsearch_list_indices,
        internal_elasticsearch_search,
    )

    # Elasticsearch tools - create wrappers that inject runtime_context
    async def internal_elasticsearch_search_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_elasticsearch_search(
            connection_name=kwargs.get("connection_name"),
            index_pattern=kwargs.get("index_pattern"),
            query=kwargs.get("query"),
            filters=kwargs.get("filters"),
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
        )

    async def internal_elasticsearch_list_indices_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_elasticsearch_list_indices(
            connection_name=kwargs.get("connection_name"), runtime_context=runtime_context
        )

    async def internal_elasticsearch_get_index_stats_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_elasticsearch_get_index_stats(
            connection_name=kwargs.get("connection_name"),
            index_pattern=kwargs.get("index_pattern"),
            runtime_context=runtime_context,
        )

    # Register all Elasticsearch tools
    registry.register_tool(
        name="internal_elasticsearch_search",
        description="""Search through Elasticsearch indices using full-text search.
        Use this to find relevant information from indexed data like Slack messages,
        documents, logs, product data, or any other data stored in Elasticsearch.

        You must first have an Elasticsearch connection configured in database connections.
        Ask the user for the connection name if you don't know it, or use
        internal_elasticsearch_list_indices to discover available indices.

        This tool is perfect for:
        - Searching historical Slack messages
        - Finding relevant documents or articles
        - Querying product information
        - Analyzing logs and events
        - Full-text search across any indexed data

        The search supports fuzzy matching and ranks results by relevance score.""",
        parameters={
            "type": "object",
            "properties": {
                "connection_name": {
                    "type": "string",
                    "description": "Name of the Elasticsearch connection from /database-connections (e.g., 'Main Elasticsearch', 'Production ES')",
                },
                "index_pattern": {
                    "type": "string",
                    "description": "Index pattern to search. Can be a specific index or pattern with wildcards (e.g., 'slack_messages_*', 'product_catalog', 'logs-2024-*')",
                },
                "query": {
                    "type": "string",
                    "description": "Search query string. Supports natural language queries that will match across all fields.",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional filters to refine the search",
                    "properties": {
                        "date_range": {
                            "type": "object",
                            "description": "Filter by date range",
                            "properties": {
                                "field": {
                                    "type": "string",
                                    "description": "Date field name (e.g., 'timestamp', 'created_at', '@timestamp')",
                                },
                                "gte": {
                                    "type": "string",
                                    "description": "Greater than or equal to (e.g., '2024-01-01', 'now-30d', 'now-1M')",
                                },
                                "lte": {
                                    "type": "string",
                                    "description": "Less than or equal to (e.g., '2024-12-31', 'now')",
                                },
                            },
                        },
                        "term_filters": {
                            "type": "object",
                            "description": "Exact match filters as key-value pairs (e.g., {'channel_name': 'product', 'user_id': 'U1234'})",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10, max: 100)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["connection_name", "index_pattern", "query"],
        },
        function=internal_elasticsearch_search_wrapper,
    )

    registry.register_tool(
        name="internal_elasticsearch_list_indices",
        description="""List all available indices in an Elasticsearch connection.

        Use this tool to discover what indices are available before searching.
        This helps you understand what data is indexed and what index patterns
        to use with internal_elasticsearch_search.

        For example, if you see indices like:
        - slack_messages_2024_12
        - slack_messages_2024_11
        - slack_messages_2024_10

        You can search all of them with pattern 'slack_messages_*'""",
        parameters={
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Name of the Elasticsearch connection"}
            },
            "required": ["connection_name"],
        },
        function=internal_elasticsearch_list_indices_wrapper,
    )

    registry.register_tool(
        name="internal_elasticsearch_get_index_stats",
        description="""Get statistics for an Elasticsearch index or pattern.

        Use this to understand the size and scope of an index before searching.
        Returns document count, storage size, and list of matching indices.""",
        parameters={
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Name of the Elasticsearch connection"},
                "index_pattern": {
                    "type": "string",
                    "description": "Index or pattern to get stats for (e.g., 'slack_messages_*')",
                },
            },
            "required": ["connection_name", "index_pattern"],
        },
        function=internal_elasticsearch_get_index_stats_wrapper,
    )

    logger.info("Registered 3 Elasticsearch tools")
