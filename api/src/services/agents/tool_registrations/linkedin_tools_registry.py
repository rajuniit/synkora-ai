"""
LinkedIn Tools Registry

Registers LinkedIn tools with the ADK tool registry.
Requires OAuth configuration via IntegrationConfig.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_linkedin_tools(registry):
    """
    Register all LinkedIn tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.linkedin_tools import (
        internal_linkedin_get_company_info,
        internal_linkedin_get_posts,
        internal_linkedin_get_profile,
        internal_linkedin_post_text,
        internal_linkedin_post_with_image,
        internal_linkedin_share_url,
    )

    # LinkedIn tools - create wrappers that inject runtime_context
    async def internal_linkedin_get_profile_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_get_profile(
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_linkedin_post_text_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_post_text(
            text=kwargs.get("text"),
            visibility=kwargs.get("visibility", "PUBLIC"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_linkedin_share_url_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_share_url(
            url=kwargs.get("url"),
            text=kwargs.get("text"),
            title=kwargs.get("title"),
            description=kwargs.get("description"),
            visibility=kwargs.get("visibility", "PUBLIC"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_linkedin_get_company_info_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_get_company_info(
            company_id=kwargs.get("company_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_linkedin_post_with_image_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_post_with_image(
            text=kwargs.get("text"),
            image_url=kwargs.get("image_url"),
            visibility=kwargs.get("visibility", "PUBLIC"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_linkedin_get_posts_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_linkedin_get_posts(
            count=kwargs.get("count", 10),
            runtime_context=runtime_context,
            config=config,
        )

    # Register LinkedIn tools
    registry.register_tool(
        name="internal_linkedin_get_profile",
        description="Get the authenticated user's LinkedIn profile information.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_linkedin_get_profile_wrapper,
    )

    registry.register_tool(
        name="internal_linkedin_post_text",
        description="Post a text update to LinkedIn. Great for sharing thoughts, updates, or insights with your professional network. Max 3000 characters.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Post content (max 3000 characters)",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["PUBLIC", "CONNECTIONS", "LOGGED_IN"],
                    "description": "Who can see the post (default: PUBLIC)",
                    "default": "PUBLIC",
                },
            },
            "required": ["text"],
        },
        function=internal_linkedin_post_text_wrapper,
    )

    registry.register_tool(
        name="internal_linkedin_share_url",
        description="Share a URL/article on LinkedIn with optional commentary. LinkedIn will automatically generate a preview card from the URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to share",
                },
                "text": {
                    "type": "string",
                    "description": "Commentary text to accompany the URL (optional)",
                },
                "title": {
                    "type": "string",
                    "description": "Title override for the shared content (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "Description override (optional)",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["PUBLIC", "CONNECTIONS", "LOGGED_IN"],
                    "description": "Who can see the post (default: PUBLIC)",
                    "default": "PUBLIC",
                },
            },
            "required": ["url"],
        },
        function=internal_linkedin_share_url_wrapper,
    )

    registry.register_tool(
        name="internal_linkedin_get_company_info",
        description="Get information about a LinkedIn company/organization.",
        parameters={
            "type": "object",
            "properties": {
                "company_id": {
                    "type": "string",
                    "description": "LinkedIn company/organization ID",
                },
            },
            "required": ["company_id"],
        },
        function=internal_linkedin_get_company_info_wrapper,
    )

    registry.register_tool(
        name="internal_linkedin_post_with_image",
        description="Post text with an image to LinkedIn. The image must be a publicly accessible URL.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Post content",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to include",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["PUBLIC", "CONNECTIONS", "LOGGED_IN"],
                    "description": "Who can see the post (default: PUBLIC)",
                    "default": "PUBLIC",
                },
            },
            "required": ["text", "image_url"],
        },
        function=internal_linkedin_post_with_image_wrapper,
    )

    registry.register_tool(
        name="internal_linkedin_get_posts",
        description="Get the authenticated user's LinkedIn post history. Retrieves recent posts including text content, visibility, and any shared articles or media.",
        parameters={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of posts to retrieve (1-100, default: 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_linkedin_get_posts_wrapper,
    )

    logger.info("Registered 6 LinkedIn tools")
