"""
Pull Request Review Tools Registry

Registers all PR review and code analysis tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_pr_review_tools(registry):
    """
    Register all PR review tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.pr_review_tools import (
        internal_analyze_pr_security,
        internal_get_file_content,
        internal_get_pr_details,
        internal_get_pr_diff,
        internal_post_pr_review,
    )

    # PR review tools - create wrappers that inject runtime_context
    async def internal_get_pr_details_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_pr_details(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_pr_diff_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_pr_diff(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_post_pr_review_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_post_pr_review(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            review_body=kwargs.get("review_body"),
            review_event=kwargs.get("review_event", "COMMENT"),
            review_comments=kwargs.get("review_comments"),
            commit_id=kwargs.get("commit_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_analyze_pr_security_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_analyze_pr_security(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            pr_number=kwargs.get("pr_number"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_file_content_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_file_content(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            path=kwargs.get("path"),
            ref=kwargs.get("ref"),
            runtime_context=runtime_context,
            config=config,
        )

    # Register all PR review tools
    registry.register_tool(
        name="internal_github_get_pr_details",
        description="Get detailed information about a GitHub pull request including changed files, commits, statistics, and existing reviews. Use this to understand what changes were made in a PR before reviewing it.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (GitHub username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_get_pr_details_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_pr_diff",
        description="Get the full unified diff of a pull request from the GitHub API. This shows all code changes in a single view. Use this for detailed code review of the actual changes. (To diff local working tree changes in a cloned repo, use internal_git_get_diff instead.)",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_get_pr_diff_wrapper,
    )

    registry.register_tool(
        name="internal_github_post_pr_review",
        description="Post a review on a GitHub pull request. You can comment, approve, or request changes. Use this after analyzing the PR to provide feedback. Be constructive and specific in your feedback.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
                "review_body": {"type": "string", "description": "Review comment body with your analysis and feedback"},
                "review_event": {
                    "type": "string",
                    "description": "Review event: COMMENT (general feedback), APPROVE (approve changes), or REQUEST_CHANGES (request modifications)",
                    "enum": ["COMMENT", "APPROVE", "REQUEST_CHANGES"],
                    "default": "COMMENT",
                },
                "commit_id": {
                    "type": "string",
                    "description": "The SHA of the PR head commit. Required when providing review_comments for inline feedback. Get this from internal_github_get_pr_details commits[-1].sha. If not provided, it will be auto-fetched.",
                },
                "review_comments": {
                    "type": "array",
                    "description": "Optional inline comments on specific lines. Requires commit_id. Each comment must have: path (file path), line (line number in file), body (comment text).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to repo root"},
                            "line": {"type": "integer", "description": "Line number in the file to comment on"},
                            "body": {"type": "string", "description": "Comment text"},
                        },
                        "required": ["path", "line", "body"],
                    },
                },
            },
            "required": ["owner", "repo", "pr_number", "review_body", "review_event"],
        },
        function=internal_post_pr_review_wrapper,
    )

    registry.register_tool(
        name="internal_github_analyze_pr_security",
        description="Analyze a pull request for security vulnerabilities and common security issues like SQL injection, XSS, hardcoded secrets, command injection, and insecure deserialization. Returns security findings with severity levels and risk score.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        },
        function=internal_analyze_pr_security_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_file_content",
        description=(
            "Get the content of a file or list contents of a directory from a GitHub repository. "
            "When the repository has been cloned with internal_git_clone_repo, pass the returned repo_path "
            "to read directly from the local filesystem (faster and avoids API limits). "
            "Falls back to GitHub API when repo_path is not provided."
        ),
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "File or directory path relative to the repository root"},
                "repo_path": {
                    "type": "string",
                    "description": "Local path to the cloned repository returned by internal_git_clone_repo. Provide this to read from the local clone instead of the GitHub API.",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch, tag, or commit SHA (only used when repo_path is not provided)",
                },
            },
            "required": ["owner", "repo", "path"],
        },
        function=internal_get_file_content_wrapper,
    )

    logger.info("Registered 5 PR review tools")
