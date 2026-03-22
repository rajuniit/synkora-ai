"""
GitHub Comment Tools Registry

Registers GitHub comment tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_github_comment_tools(registry):
    """
    Register all GitHub comment tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.github_comment_tools import (
        internal_github_delete_comment,
        internal_github_get_comment,
        internal_github_list_comments,
        internal_github_post_issue_comment,
        internal_github_post_pr_review_comment,
        internal_github_reply_to_review_comment,
        internal_github_update_comment,
    )

    # Create wrappers that inject runtime_context

    async def internal_github_post_issue_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_post_issue_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            body=kwargs.get("body"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_update_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_update_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            comment_id=kwargs.get("comment_id"),
            body=kwargs.get("body"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_delete_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_delete_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            comment_id=kwargs.get("comment_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_list_comments_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_list_comments(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            comment_id=kwargs.get("comment_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_post_pr_review_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_post_pr_review_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            body=kwargs.get("body"),
            commit_id=kwargs.get("commit_id"),
            path=kwargs.get("path"),
            line=kwargs.get("line"),
            side=kwargs.get("side", "RIGHT"),
            start_line=kwargs.get("start_line"),
            start_side=kwargs.get("start_side"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_reply_to_review_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_reply_to_review_comment(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            comment_id=kwargs.get("comment_id"),
            body=kwargs.get("body"),
            runtime_context=runtime_context,
            config=config,
        )

    # Register tools

    registry.register_tool(
        name="internal_github_post_issue_comment",
        description="Post a comment on a GitHub issue or pull request. GitHub uses the same API for both — pass an issue number or PR number as issue_number.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (GitHub username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number or pull request number"},
                "body": {"type": "string", "description": "Comment body (markdown supported)"},
            },
            "required": ["owner", "repo", "issue_number", "body"],
        },
        function=internal_github_post_issue_comment_wrapper,
    )

    registry.register_tool(
        name="internal_github_update_comment",
        description="Update an existing comment on a GitHub issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID to update"},
                "body": {"type": "string", "description": "New comment body (markdown supported)"},
            },
            "required": ["owner", "repo", "comment_id", "body"],
        },
        function=internal_github_update_comment_wrapper,
    )

    registry.register_tool(
        name="internal_github_delete_comment",
        description="Delete a comment from a GitHub issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID to delete"},
            },
            "required": ["owner", "repo", "comment_id"],
        },
        function=internal_github_delete_comment_wrapper,
    )

    registry.register_tool(
        name="internal_github_list_comments",
        description="List all comments on a GitHub issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue or PR number"},
                "per_page": {
                    "type": "integer",
                    "description": "Number of comments per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_list_comments_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_comment",
        description="Get a specific comment from a GitHub issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "comment_id": {"type": "integer", "description": "Comment ID"},
            },
            "required": ["owner", "repo", "comment_id"],
        },
        function=internal_github_get_comment_wrapper,
    )

    registry.register_tool(
        name="internal_github_post_pr_review_comment",
        description="Post a review comment on a specific line in a pull request diff.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "body": {"type": "string", "description": "Comment body (markdown supported)"},
                "commit_id": {"type": "string", "description": "SHA of the commit to comment on"},
                "path": {"type": "string", "description": "Relative file path to comment on"},
                "line": {"type": "integer", "description": "Line number in the diff to comment on"},
                "side": {
                    "type": "string",
                    "enum": ["LEFT", "RIGHT"],
                    "description": "Which side of the diff to comment on (default: RIGHT)",
                    "default": "RIGHT",
                },
                "start_line": {"type": "integer", "description": "First line for multi-line comment (optional)"},
                "start_side": {
                    "type": "string",
                    "enum": ["LEFT", "RIGHT"],
                    "description": "Side for start_line (optional)",
                },
            },
            "required": ["owner", "repo", "pr_number", "body", "commit_id", "path"],
        },
        function=internal_github_post_pr_review_comment_wrapper,
    )

    registry.register_tool(
        name="internal_github_reply_to_review_comment",
        description="Reply to an existing review comment on a pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "comment_id": {"type": "integer", "description": "ID of the review comment to reply to"},
                "body": {"type": "string", "description": "Reply body (markdown supported)"},
            },
            "required": ["owner", "repo", "pr_number", "comment_id", "body"],
        },
        function=internal_github_reply_to_review_comment_wrapper,
    )

    logger.info("Registered 7 GitHub comment tools")
