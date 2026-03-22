"""
Git Branch Tools Registry.

Registers tools for branch lifecycle: creating, switching, listing, and pulling.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_git_branch_tools(registry):
    """Register git branch operation tools with the ADK tool registry."""
    from src.services.agents.internal_tools.git_branch_tools import (
        internal_git_create_branch,
        internal_git_list_branches,
        internal_git_pull_changes,
        internal_git_switch_branch,
    )

    async def internal_git_create_branch_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_create_branch(
            repo_path=kwargs.get("repo_path"),
            branch_name=kwargs.get("branch_name"),
            from_branch=kwargs.get("from_branch", "main"),
            config=config,
        )

    async def internal_git_switch_branch_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_switch_branch(
            repo_path=kwargs.get("repo_path"),
            branch_name=kwargs.get("branch_name"),
            config=config,
        )

    async def internal_git_list_branches_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_list_branches(
            repo_path=kwargs.get("repo_path"),
            include_remote=kwargs.get("include_remote", False),
            config=config,
        )

    async def internal_git_pull_changes_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_pull_changes(
            repo_path=kwargs.get("repo_path"),
            remote=kwargs.get("remote", "origin"),
            branch=kwargs.get("branch"),
            config=config,
        )

    registry.register_tool(
        name="internal_git_create_branch",
        description="Create a new branch in a local Git repository. Fetches latest changes and creates the branch from the specified source branch.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "branch_name": {"type": "string", "description": "Name of the new branch to create"},
                "from_branch": {
                    "type": "string",
                    "description": "Branch to create from (default: 'main')",
                    "default": "main",
                },
            },
            "required": ["repo_path", "branch_name"],
        },
        function=internal_git_create_branch_wrapper,
    )

    registry.register_tool(
        name="internal_git_switch_branch",
        description="Switch to an existing branch in the repository.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "branch_name": {"type": "string", "description": "Name of the branch to switch to"},
            },
            "required": ["repo_path", "branch_name"],
        },
        function=internal_git_switch_branch_wrapper,
    )

    registry.register_tool(
        name="internal_git_list_branches",
        description="List all branches in the repository, both local and remote. Shows the current branch.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "include_remote": {
                    "type": "boolean",
                    "description": "Whether to include remote branches in the list (default: false)",
                    "default": False,
                },
            },
            "required": ["repo_path"],
        },
        function=internal_git_list_branches_wrapper,
    )

    registry.register_tool(
        name="internal_git_pull_changes",
        description="Pull changes from remote repository to sync the local clone with the latest changes.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "remote": {
                    "type": "string",
                    "description": "Remote name to pull from (default: 'origin')",
                    "default": "origin",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name to pull (optional, uses current branch if not specified)",
                },
            },
            "required": ["repo_path"],
        },
        function=internal_git_pull_changes_wrapper,
    )

    logger.info("Registered 4 git branch tools")
