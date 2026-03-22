"""
Hacker News Tools Registry

Registers Hacker News tools with the ADK tool registry.
No authentication required - uses public HN API.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_hackernews_tools(registry):
    """
    Register all Hacker News tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.hackernews_tools import (
        internal_hackernews_get_ask_hn,
        internal_hackernews_get_best_stories,
        internal_hackernews_get_new_stories,
        internal_hackernews_get_show_hn,
        internal_hackernews_get_story_details,
        internal_hackernews_get_top_stories,
        internal_hackernews_get_trending_topics,
        internal_hackernews_get_user,
        internal_hackernews_search,
    )

    # Hacker News tools - create wrappers that inject runtime_context
    async def internal_hackernews_get_top_stories_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_top_stories(
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_new_stories_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_new_stories(
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_best_stories_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_best_stories(
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_ask_hn_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_ask_hn(
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_show_hn_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_show_hn(
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_story_details_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_story_details(
            story_id=kwargs.get("story_id"),
            include_comments=kwargs.get("include_comments", False),
            comment_limit=kwargs.get("comment_limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_search_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_search(
            query=kwargs.get("query"),
            search_type=kwargs.get("search_type", "story"),
            sort_by=kwargs.get("sort_by", "relevance"),
            time_range=kwargs.get("time_range"),
            limit=kwargs.get("limit", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_user_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_user(
            username=kwargs.get("username"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_hackernews_get_trending_topics_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_hackernews_get_trending_topics(
            limit=kwargs.get("limit", 20),
            runtime_context=runtime_context,
            config=config,
        )

    # Register Hacker News tools
    registry.register_tool(
        name="internal_hackernews_get_top_stories",
        description="Get the current top stories on Hacker News front page. These are the most popular stories right now in the tech community.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stories to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_top_stories_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_new_stories",
        description="Get the newest stories on Hacker News. Good for discovering fresh content before it trends.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stories to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_new_stories_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_best_stories",
        description="Get the best stories on Hacker News (highest voted over time). Great for finding high-quality, well-received content.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stories to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_best_stories_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_ask_hn",
        description="Get Ask HN posts - questions and discussions from the Hacker News community. Good for understanding what the community is curious about.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of posts to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_ask_hn_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_show_hn",
        description="Get Show HN posts - projects and creations shared by the community. Good for discovering new tools, startups, and side projects.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of posts to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_show_hn_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_story_details",
        description="Get detailed information about a specific Hacker News story, optionally including top-level comments.",
        parameters={
            "type": "object",
            "properties": {
                "story_id": {
                    "type": "integer",
                    "description": "The Hacker News story ID",
                },
                "include_comments": {
                    "type": "boolean",
                    "description": "Whether to fetch top-level comments (default False)",
                    "default": False,
                },
                "comment_limit": {
                    "type": "integer",
                    "description": "Max number of comments to fetch (default 10)",
                    "default": 10,
                },
            },
            "required": ["story_id"],
        },
        function=internal_hackernews_get_story_details_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_search",
        description="Search Hacker News for stories or comments matching a query. Supports filtering by type, time range, and sort order.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["story", "comment", "all"],
                    "description": "Type of content to search (default: story)",
                    "default": "story",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "date"],
                    "description": "Sort by relevance or date (default: relevance)",
                    "default": "relevance",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["24h", "week", "month", "year"],
                    "description": "Filter by time range (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        function=internal_hackernews_search_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_user",
        description="Get information about a Hacker News user including their karma and submission count.",
        parameters={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "The HN username",
                },
            },
            "required": ["username"],
        },
        function=internal_hackernews_get_user_wrapper,
    )

    registry.register_tool(
        name="internal_hackernews_get_trending_topics",
        description="Analyze current top stories to identify trending topics on Hacker News. Returns a summary of what's trending with example stories.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top stories to analyze (default 20)",
                    "default": 20,
                },
            },
            "required": [],
        },
        function=internal_hackernews_get_trending_topics_wrapper,
    )

    logger.info("Registered 9 Hacker News tools")
