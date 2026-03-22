"""
GitHub PR Management Tools Registry

Registers GitHub pull request management tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_github_pr_management_tools(registry):
    """
    Register all GitHub PR management tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.github_pr_management_tools import (
        internal_github_add_labels,
        internal_github_close_pr,
        internal_github_create_pr,
        internal_github_merge_pr,
        internal_github_remove_label,
        internal_github_remove_reviewers,
        internal_github_reopen_pr,
        internal_github_request_reviewers,
        internal_github_update_branch,
        internal_github_update_pr,
    )

    # Create wrappers that inject runtime_context

    async def internal_github_merge_pr_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_merge_pr(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            commit_title=kwargs.get("commit_title"),
            commit_message=kwargs.get("commit_message"),
            merge_method=kwargs.get("merge_method", "merge"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_close_pr_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_close_pr(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_reopen_pr_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_reopen_pr(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_update_pr_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_update_pr(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            title=kwargs.get("title"),
            body=kwargs.get("body"),
            base=kwargs.get("base"),
            maintainer_can_modify=kwargs.get("maintainer_can_modify"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_request_reviewers_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_request_reviewers(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            reviewers=kwargs.get("reviewers"),
            team_reviewers=kwargs.get("team_reviewers"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_remove_reviewers_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_remove_reviewers(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            reviewers=kwargs.get("reviewers"),
            team_reviewers=kwargs.get("team_reviewers"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_add_labels_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_add_labels(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            labels=kwargs.get("labels"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_remove_label_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_remove_label(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            issue_number=kwargs.get("issue_number"),
            label=kwargs.get("label"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_update_branch_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_update_branch(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            expected_head_sha=kwargs.get("expected_head_sha"),
            runtime_context=runtime_context,
            config=config,
        )

    # Register tools

    registry.register_tool(
        name="internal_github_merge_pr",
        description="Merge a pull request. Supports merge, squash, and rebase methods.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "commit_title": {"type": "string", "description": "Title for the merge commit (optional)"},
                "commit_message": {"type": "string", "description": "Message for the merge commit (optional)"},
                "merge_method": {
                    "type": "string",
                    "enum": ["merge", "squash", "rebase"],
                    "description": "Merge method (default: merge)",
                    "default": "merge",
                },
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_merge_pr_wrapper,
    )

    registry.register_tool(
        name="internal_github_close_pr",
        description="Close a pull request without merging.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_close_pr_wrapper,
    )

    registry.register_tool(
        name="internal_github_reopen_pr",
        description="Reopen a closed pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_reopen_pr_wrapper,
    )

    registry.register_tool(
        name="internal_github_update_pr",
        description="Update a pull request's title, body, or base branch.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "title": {"type": "string", "description": "New title for the PR (optional)"},
                "body": {"type": "string", "description": "New body/description for the PR (optional)"},
                "base": {"type": "string", "description": "New base branch (optional)"},
                "maintainer_can_modify": {
                    "type": "boolean",
                    "description": "Allow maintainers to push to head branch (optional)",
                },
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_update_pr_wrapper,
    )

    registry.register_tool(
        name="internal_github_request_reviewers",
        description="Request reviewers for a pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of GitHub usernames to request as reviewers",
                },
                "team_reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of team slugs to request as reviewers",
                },
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_request_reviewers_wrapper,
    )

    registry.register_tool(
        name="internal_github_remove_reviewers",
        description="Remove requested reviewers from a pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of GitHub usernames to remove",
                },
                "team_reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of team slugs to remove",
                },
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_remove_reviewers_wrapper,
    )

    registry.register_tool(
        name="internal_github_add_labels",
        description="Add labels to an issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue or PR number"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names to add",
                },
            },
            "required": ["owner", "repo", "issue_number", "labels"],
        },
        function=internal_github_add_labels_wrapper,
    )

    registry.register_tool(
        name="internal_github_remove_label",
        description="Remove a label from an issue or pull request.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "issue_number": {"type": "integer", "description": "Issue or PR number"},
                "label": {"type": "string", "description": "Label name to remove"},
            },
            "required": ["owner", "repo", "issue_number", "label"],
        },
        function=internal_github_remove_label_wrapper,
    )

    registry.register_tool(
        name="internal_github_update_branch",
        description="Update a pull request's head branch with the latest changes from the base branch.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "expected_head_sha": {
                    "type": "string",
                    "description": "Expected SHA of the PR's head ref for optimistic locking (optional)",
                },
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_github_update_branch_wrapper,
    )

    async def internal_github_create_pr_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_create_pr(
            repo_owner=kwargs.get("repo_owner"),
            repo_name=kwargs.get("repo_name"),
            title=kwargs.get("title"),
            head_branch=kwargs.get("head_branch"),
            base_branch=kwargs.get("base_branch", "main"),
            body=kwargs.get("body", ""),
            draft=kwargs.get("draft", False),
            config=config,
            runtime_context=runtime_context,
        )

    registry.register_tool(
        name="internal_github_create_pr",
        description="Create a pull request using the GitHub API. Uses the configured GitHub OAuth token for authentication. Use this after pushing a branch with internal_git_commit_and_push.",
        parameters={
            "type": "object",
            "properties": {
                "repo_owner": {"type": "string", "description": "Repository owner (username or organization name)"},
                "repo_name": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "Pull request title"},
                "head_branch": {"type": "string", "description": "Branch containing the changes (source branch)"},
                "base_branch": {
                    "type": "string",
                    "description": "Branch to merge into (target branch, default: 'main')",
                    "default": "main",
                },
                "body": {
                    "type": "string",
                    "description": "Pull request description/body (markdown supported)",
                    "default": "",
                },
                "draft": {
                    "type": "boolean",
                    "description": "Whether to create as a draft PR (default: false)",
                    "default": False,
                },
            },
            "required": ["repo_owner", "repo_name", "title", "head_branch"],
        },
        function=internal_github_create_pr_wrapper,
    )

    logger.info("Registered 10 GitHub PR management tools")
