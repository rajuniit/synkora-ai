"""
GitHub Repo Tools Registry

Registers GitHub repository tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_github_repo_tools(registry):
    """
    Register all GitHub repository tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.github_repo_tools import (
        internal_github_get_branches,
        internal_github_get_commits,
        internal_github_get_contributors,
        internal_github_get_file_content,
        internal_github_get_readme,
        internal_github_get_repo_info,
        internal_github_list_repo_contents,
        internal_github_search_code,
        internal_github_search_repos,
    )

    # Create wrappers that inject runtime_context

    async def internal_github_get_repo_info_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_repo_info(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_readme_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_readme(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            ref=kwargs.get("ref"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_list_repo_contents_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_list_repo_contents(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            path=kwargs.get("path", ""),
            ref=kwargs.get("ref"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_file_content_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_file_content(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            path=kwargs.get("path"),
            ref=kwargs.get("ref"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_search_code_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_search_code(
            query=kwargs.get("query"),
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            language=kwargs.get("language"),
            path=kwargs.get("path"),
            extension=kwargs.get("extension"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_search_repos_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_search_repos(
            query=kwargs.get("query"),
            language=kwargs.get("language"),
            sort=kwargs.get("sort"),
            order=kwargs.get("order", "desc"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_branches_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_branches(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            protected=kwargs.get("protected"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_commits_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_commits(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            sha=kwargs.get("sha"),
            path=kwargs.get("path"),
            author=kwargs.get("author"),
            since=kwargs.get("since"),
            until=kwargs.get("until"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_github_get_contributors_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_github_get_contributors(
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            per_page=kwargs.get("per_page", 30),
            page=kwargs.get("page", 1),
            runtime_context=runtime_context,
            config=config,
        )

    # Register tools

    registry.register_tool(
        name="internal_github_get_repo_info",
        description="Get detailed information about a GitHub repository including stats, settings, and metadata.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (GitHub username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_get_repo_info_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_readme",
        description="Get the README file content from a repository.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "ref": {"type": "string", "description": "Branch, tag, or commit SHA (optional)"},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_get_readme_wrapper,
    )

    registry.register_tool(
        name="internal_github_list_repo_contents",
        description="List contents of a directory in a repository. Returns files and subdirectories.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "Path to directory (empty for root)", "default": ""},
                "ref": {"type": "string", "description": "Branch, tag, or commit SHA (optional)"},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_list_repo_contents_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_file_content",
        description="Get the content of a specific file from a repository.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "path": {"type": "string", "description": "Path to file"},
                "ref": {"type": "string", "description": "Branch, tag, or commit SHA (optional)"},
            },
            "required": ["owner", "repo", "path"],
        },
        function=internal_github_get_file_content_wrapper,
    )

    registry.register_tool(
        name="internal_github_search_code",
        description="Search for code across GitHub repositories.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (code to find)"},
                "owner": {"type": "string", "description": "Filter by repository owner"},
                "repo": {"type": "string", "description": "Filter by specific repo as 'owner/repo'"},
                "language": {"type": "string", "description": "Filter by programming language"},
                "path": {"type": "string", "description": "Filter by file path"},
                "extension": {"type": "string", "description": "Filter by file extension"},
                "per_page": {
                    "type": "integer",
                    "description": "Number of results per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["query"],
        },
        function=internal_github_search_code_wrapper,
    )

    registry.register_tool(
        name="internal_github_search_repos",
        description="Search for repositories across GitHub.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "language": {"type": "string", "description": "Filter by programming language"},
                "sort": {
                    "type": "string",
                    "enum": ["stars", "forks", "help-wanted-issues", "updated"],
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
        function=internal_github_search_repos_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_branches",
        description="List branches in a repository.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "protected": {"type": "boolean", "description": "Filter by protected status"},
                "per_page": {
                    "type": "integer",
                    "description": "Number of branches per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_get_branches_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_commits",
        description="List commits in a repository with optional filtering.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "sha": {"type": "string", "description": "Branch name, tag, or commit SHA to start from"},
                "path": {"type": "string", "description": "Filter by file path"},
                "author": {"type": "string", "description": "Filter by author username or email"},
                "since": {"type": "string", "description": "Only commits after this date (ISO 8601)"},
                "until": {"type": "string", "description": "Only commits before this date (ISO 8601)"},
                "per_page": {
                    "type": "integer",
                    "description": "Number of commits per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_get_commits_wrapper,
    )

    registry.register_tool(
        name="internal_github_get_contributors",
        description="List contributors to a repository with commit counts.",
        parameters={
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "per_page": {
                    "type": "integer",
                    "description": "Number of contributors per page (max 100, default 30)",
                    "default": 30,
                },
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
            },
            "required": ["owner", "repo"],
        },
        function=internal_github_get_contributors_wrapper,
    )

    logger.info("Registered 9 GitHub repo tools")
