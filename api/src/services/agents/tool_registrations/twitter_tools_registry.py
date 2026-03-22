"""
Twitter/X Tools Registry

Registers Twitter tools with the ADK tool registry.
Requires OAuth configuration via IntegrationConfig.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_twitter_tools(registry):
    """
    Register all Twitter tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.twitter_tools import (
        internal_twitter_delete_tweet,
        internal_twitter_get_bookmarks,
        internal_twitter_get_my_profile,
        internal_twitter_get_user_by_username,
        internal_twitter_get_user_timeline,
        internal_twitter_post_tweet,
        internal_twitter_search_tweets,
    )

    # Twitter tools - create wrappers that inject runtime_context
    async def internal_twitter_get_user_timeline_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_get_user_timeline(
            user_id=kwargs.get("user_id"),
            username=kwargs.get("username"),
            max_results=kwargs.get("max_results", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_get_bookmarks_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_get_bookmarks(
            max_results=kwargs.get("max_results", 10),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_post_tweet_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_post_tweet(
            text=kwargs.get("text"),
            reply_to_tweet_id=kwargs.get("reply_to_tweet_id"),
            quote_tweet_id=kwargs.get("quote_tweet_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_search_tweets_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_search_tweets(
            query=kwargs.get("query"),
            max_results=kwargs.get("max_results", 10),
            sort_order=kwargs.get("sort_order", "relevancy"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_get_user_by_username_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_get_user_by_username(
            username=kwargs.get("username"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_get_my_profile_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_get_my_profile(
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_twitter_delete_tweet_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_twitter_delete_tweet(
            tweet_id=kwargs.get("tweet_id"),
            runtime_context=runtime_context,
            config=config,
        )

    # Register Twitter tools
    registry.register_tool(
        name="internal_twitter_get_user_timeline",
        description="Get tweets from a user's timeline. Use this to read what a specific user has posted. Provide either user_id or username.",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Twitter user ID (optional if username provided)",
                },
                "username": {
                    "type": "string",
                    "description": "Twitter username/handle without @ (optional if user_id provided)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tweets to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_twitter_get_user_timeline_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_get_bookmarks",
        description="Get your bookmarked tweets. Use this to retrieve saved tweets for reference or processing.",
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of bookmarks to return (default 10, max 100)",
                    "default": 10,
                },
            },
            "required": [],
        },
        function=internal_twitter_get_bookmarks_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_post_tweet",
        description="Post a new tweet to Twitter/X. Can also reply to or quote existing tweets. Max 280 characters.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Tweet text (max 280 characters)",
                },
                "reply_to_tweet_id": {
                    "type": "string",
                    "description": "ID of tweet to reply to (optional)",
                },
                "quote_tweet_id": {
                    "type": "string",
                    "description": "ID of tweet to quote (optional)",
                },
            },
            "required": ["text"],
        },
        function=internal_twitter_post_tweet_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_search_tweets",
        description="Search for tweets matching a query. Supports Twitter search operators like 'from:user' and '-filter:retweets'.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports Twitter search operators)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (default 10, max 100)",
                    "default": 10,
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["relevancy", "recency"],
                    "description": "Sort by relevance or recency (default: relevancy)",
                    "default": "relevancy",
                },
            },
            "required": ["query"],
        },
        function=internal_twitter_search_tweets_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_get_user_by_username",
        description="Get Twitter user information by their username/handle.",
        parameters={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Twitter username/handle (without @)",
                },
            },
            "required": ["username"],
        },
        function=internal_twitter_get_user_by_username_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_get_my_profile",
        description="Get the authenticated user's Twitter profile information.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=internal_twitter_get_my_profile_wrapper,
    )

    registry.register_tool(
        name="internal_twitter_delete_tweet",
        description="Delete one of your tweets by its ID.",
        parameters={
            "type": "object",
            "properties": {
                "tweet_id": {
                    "type": "string",
                    "description": "ID of the tweet to delete",
                },
            },
            "required": ["tweet_id"],
        },
        function=internal_twitter_delete_tweet_wrapper,
    )

    logger.info("Registered 7 Twitter tools")
