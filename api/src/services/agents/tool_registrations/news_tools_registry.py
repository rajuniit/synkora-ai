"""
News Tools Registry

Registers NewsAPI and RSS feed tools with the ADK tool registry.
NewsAPI requires a configured OAuth app (auth_method=api_token).
RSS feed parsing requires no credentials.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_news_tools(registry) -> None:
    """
    Register all news tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.news_tools import (
        internal_fetch_rss_feed,
        internal_news_search,
    )

    async def news_search_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_news_search(
            query=kwargs.get("query"),
            category=kwargs.get("category"),
            language=kwargs.get("language", "en"),
            from_date=kwargs.get("from_date"),
            page_size=kwargs.get("page_size", 20),
            sort_by=kwargs.get("sort_by", "publishedAt"),
            runtime_context=runtime_context,
            config=config,
        )

    async def rss_feed_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_fetch_rss_feed(
            url=kwargs.get("url"),
            max_items=kwargs.get("max_items", 20),
            filter_hours=kwargs.get("filter_hours", 24),
            runtime_context=runtime_context,
            config=config,
        )

    registry.register_tool(
        name="internal_news_search",
        description=(
            "Search for recent news articles using NewsAPI across 150,000+ sources. "
            "Returns titles, summaries, URLs, and publication dates. "
            "Requires a NewsAPI OAuth app to be configured and connected."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'artificial intelligence'",
                },
                "category": {
                    "type": "string",
                    "description": "Category: technology, science, business, health, entertainment, sports",
                },
                "language": {
                    "type": "string",
                    "description": "Language code (en, de, fr, etc.)",
                    "default": "en",
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD, defaults to yesterday",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of articles to return (max 100)",
                    "default": 20,
                },
                "sort_by": {
                    "type": "string",
                    "description": "Sort order: publishedAt | relevancy | popularity",
                    "default": "publishedAt",
                },
            },
            "required": ["query"],
        },
        function=news_search_wrapper,
    )

    registry.register_tool(
        name="internal_fetch_rss_feed",
        description=(
            "Fetch and parse an RSS or Atom feed. Works reliably on all major news sites "
            "(TechCrunch, The Verge, Wired, ArsTechnica, etc.) without getting blocked. "
            "Use this instead of web_fetch for news sites."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "RSS or Atom feed URL",
                },
                "max_items": {
                    "type": "integer",
                    "description": "Maximum items to return",
                    "default": 20,
                },
                "filter_hours": {
                    "type": "integer",
                    "description": "Only return items from last N hours (0 = no filter)",
                    "default": 24,
                },
            },
            "required": ["url"],
        },
        function=rss_feed_wrapper,
    )

    logger.info("Registered 2 news tools: internal_news_search, internal_fetch_rss_feed")
