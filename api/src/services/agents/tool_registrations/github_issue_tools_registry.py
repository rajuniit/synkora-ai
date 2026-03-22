"""
GitHub Issue Tools Registry

Registers GitHub issue tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_github_issue_tools(registry):
    """
    Register all GitHub issue tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.github_issue_tools import (
        internal_github_assign_issue,
        internal_github_close_issue,
        internal_github_create_issue,
        internal_github_get_issue,
        internal_github_list_issues,
        internal_github_lock_issue,
        internal_github_reopen_issue,
        internal_github_search_issues,
        internal_github_unassign_issue,
        internal_github_unlock_issue,
        internal_github_update_issue,
    )

    # Create wrappers that inject runtime_context

    async def internal_github_create_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_create_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            title=kwargs.get("title"),
            body=kwargs.get("body", ""),
            labels=kwargs.get("labels"),
            assignees=kwargs.get("assignees"),
            milestone=kwargs.get("milestone"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_list_issues_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_list_issues(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            state=kwargs.get("state", "open"),
            labels=kwargs.get("labels"),
            assignee=kwargs.get("assignee"),
            creator=kwargs.get("creator"),
            mentioned=kwargs.get("mentioned"),
            sort=kwargs.get("sort", "created"),
            direction=kwargs.get("direction", "desc"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_update_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_update_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            title=kwargs.get("title"),
            body=kwargs.get("body"),
            state=kwargs.get("state"),
            state_reason=kwargs.get("state_reason"),
            labels=kwargs.get("labels"),
            assignees=kwargs.get("assignees"),
            milestone=kwargs.get("milestone"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_close_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_close_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            state_reason=kwargs.get("state_reason", "completed"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_reopen_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_reopen_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_assign_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_assign_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            assignees=kwargs.get("assignees"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_unassign_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_unassign_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            assignees=kwargs.get("assignees"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_lock_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_lock_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            lock_reason=kwargs.get("lock_reason"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_unlock_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_unlock_issue(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_search_issues_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_search_issues(
            query=kwargs.get("query"),
            sort=kwargs.get("sort"),
            order=kwargs.get("order", "desc"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    # Register tools

    registry.register_tool(
        name="internal_github_create_issue",
        description="Create a new issue in a GitHub repository.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "Issue title"},
                "body": {"type": "string", "description": "Issue body (markdown supported)", "default": ""},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names to add",
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of GitHub usernames to assign",
                },
                "milestone": {"type": "integer", "description": "Milestone number to associate"},
            },
            "required": ["owner", "repo", "title"],
        },
        function=internal_github_create_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_issue",
        description="Get details of a specific issue.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_get_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_list_issues",
        description="List issues in a repository. Excludes pull requests.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by state (default: open)",
                    "default": "open",
                },
                "labels": {"type": "string", "description": "Comma-separated list of label names to filter by"},
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee ('*' for any, 'none' for unassigned)",
                },
                "creator": {"type": "string", "description": "Filter by issue creator username"},
                "mentioned": {"type": "string", "description": "Filter by mentioned username"},
                "sort": {
                    "type": "string",
                    "enum": ["created", "updated", "comments"],
                    "description": "Sort by (default: created)",
                    "default": "created",
                },
                "direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort direction (default: desc)",
                    "default": "desc",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of issues per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_list_issues_wrapper,
    )

    registry.register_tool(
        name="internal_github_update_issue",
        description="Update an issue's title, body, state, labels, or assignees.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
                "title": {"type": "string", "description": "New title"},
                "body": {"type": "string", "description": "New body/description"},
                "state": {"type": "string", "enum": ["open", "closed"], "description": "New state"},
                "state_reason": {
                    "type": "string",
                    "enum": ["completed", "not_planned", "reopened"],
                    "description": "Reason for state change",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Replace labels with this list",
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Replace assignees with this list",
                },
                "milestone": {"type": "integer", "description": "Milestone number (0 to remove)"},
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_update_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_close_issue",
        description="Close an issue.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
                "state_reason": {
                    "type": "string",
                    "enum": ["completed", "not_planned"],
                    "description": "Reason for closing (default: completed)",
                    "default": "completed",
                },
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_close_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_reopen_issue",
        description="Reopen a closed issue.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_reopen_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_assign_issue",
        description="Add assignees to an issue.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of GitHub usernames to assign",
                },
            },
            "required": ["owner", "repo", "issue_number", "assignees"],
        },
        function=internal_github_assign_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_unassign_issue",
        description="Remove assignees from an issue.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of GitHub usernames to remove",
                },
            },
            "required": ["owner", "repo", "issue_number", "assignees"],
        },
        function=internal_github_unassign_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_lock_issue",
        description="Lock an issue to prevent comments.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
                "lock_reason": {
                    "type": "string",
                    "enum": ["off-topic", "too heated", "resolved", "spam"],
                    "description": "Reason for locking (optional)",
                },
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_lock_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_unlock_issue",
        description="Unlock an issue to allow comments.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue number"},
            },
            "required": ["owner", "repo", "issue_number"],
        },
        function=internal_github_unlock_issue_wrapper,
    )

    registry.register_tool(
        name="internal_github_search_issues",
        description="Search for issues and pull requests across GitHub.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'repo:owner/repo is:issue is:open label:bug')",
                },
                "sort": {
                    "type": "string",
                    "enum": ["comments", "reactions", "created", "updated"],
                    "description": "Sort by (optional)",
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order (default: desc)",
                    "default": "desc",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of results per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["query"],
        },
        function=internal_github_search_issues_wrapper,
    )

    logger.info("Registered 11 GitHub issue tools")
