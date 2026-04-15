"""
Knowledge Base Ingest Tools Registry.

Registers tools that allow agents to crawl URLs and add text content
into knowledge bases directly from a conversation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_kb_ingest_tools(registry) -> None:
    """Register KB ingest tools with the ADK tool registry."""
    from src.services.agents.internal_tools.kb_ingest_tools import (
        internal_kb_add_text,
        internal_kb_crawl_url,
    )

    async def internal_kb_crawl_url_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_kb_crawl_url(
            url=kwargs.get("url"),
            knowledge_base_id=kwargs.get("knowledge_base_id"),
            include_subpages=kwargs.get("include_subpages", True),
            max_pages=kwargs.get("max_pages", 50),
            config=config,
        )

    async def internal_kb_add_text_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_kb_add_text(
            title=kwargs.get("title"),
            content=kwargs.get("content"),
            knowledge_base_id=kwargs.get("knowledge_base_id"),
            config=config,
        )

    registry.register_tool(
        name="internal_kb_crawl_url",
        function=internal_kb_crawl_url_wrapper,
        description=(
            "Crawl a public URL and persist its content into a knowledge base. "
            "Set include_subpages=true and a high max_pages to crawl an entire app or documentation site. "
            "The crawl runs as a background task — this call returns immediately."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The public HTTP/HTTPS starting URL to crawl.",
                },
                "knowledge_base_id": {
                    "type": "integer",
                    "description": "Numeric ID of the knowledge base to store content in.",
                },
                "include_subpages": {
                    "type": "boolean",
                    "description": (
                        "Follow same-domain links to crawl the entire site. "
                        "Set true to crawl a whole app or docs site. Default: true."
                    ),
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum pages to crawl (1–500). Default: 50.",
                },
            },
            "required": ["url", "knowledge_base_id"],
        },
        tool_category="kb_ingest_tools",
    )

    registry.register_tool(
        name="internal_kb_add_text",
        function=internal_kb_add_text_wrapper,
        description=(
            "Add text content (how-to guides, manuals, FAQs, or any reference material) "
            "directly to a knowledge base. The content is chunked, embedded, and indexed "
            "so agents can retrieve it in future conversations."
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "A clear, descriptive title for the document (e.g. 'How to reset a password').",
                },
                "content": {
                    "type": "string",
                    "description": "Full text content to store in the knowledge base.",
                },
                "knowledge_base_id": {
                    "type": "integer",
                    "description": "Numeric ID of the knowledge base to store content in.",
                },
            },
            "required": ["title", "content", "knowledge_base_id"],
        },
        tool_category="kb_ingest_tools",
    )
