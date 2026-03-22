"""
Git Commit Tools Registry.

Registers tools for working tree inspection and commit operations:
status, diff, commit history, commit-and-push, cherry-pick, and revert.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_git_commit_tools(registry):
    """Register git working tree and commit tools with the ADK tool registry."""
    from src.services.agents.internal_tools.git_commit_tools import (
        internal_git_cherry_pick,
        internal_git_commit_and_push,
        internal_git_get_commit_history,
        internal_git_get_diff,
        internal_git_get_status,
        internal_git_revert_commit,
    )

    async def internal_git_get_status_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_get_status(
            repo_path=kwargs.get("repo_path"),
            config=config,
        )

    async def internal_git_get_diff_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_get_diff(
            repo_path=kwargs.get("repo_path"),
            file_path=kwargs.get("file_path"),
            staged=kwargs.get("staged", False),
            config=config,
        )

    async def internal_git_commit_and_push_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_commit_and_push(
            repo_path=kwargs.get("repo_path"),
            branch_name=kwargs.get("branch_name"),
            commit_message=kwargs.get("commit_message"),
            config=config,
        )

    async def internal_git_get_commit_history_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_get_commit_history(
            repo_path=kwargs.get("repo_path"),
            max_commits=kwargs.get("max_commits", 10),
            branch=kwargs.get("branch"),
            config=config,
        )

    async def internal_git_cherry_pick_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_cherry_pick(
            repo_path=kwargs.get("repo_path"),
            commit_hash=kwargs.get("commit_hash"),
            config=config,
        )

    async def internal_git_revert_commit_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_git_revert_commit(
            repo_path=kwargs.get("repo_path"),
            commit_hash=kwargs.get("commit_hash"),
            config=config,
        )

    registry.register_tool(
        name="internal_git_get_status",
        description="Get the status of a Git repository showing modified, staged, and untracked files.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
            },
            "required": ["repo_path"],
        },
        function=internal_git_get_status_wrapper,
    )

    registry.register_tool(
        name="internal_git_get_diff",
        description="Get diff of local working tree changes in a cloned repository. Shows what has changed before committing. For a GitHub PR diff without cloning, use internal_github_get_pr_diff instead.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "file_path": {
                    "type": "string",
                    "description": "Specific file to get diff for (optional, shows all changes if not specified)",
                },
                "staged": {
                    "type": "boolean",
                    "description": "Get staged changes instead of working directory changes (default: false)",
                    "default": False,
                },
            },
            "required": ["repo_path"],
        },
        function=internal_git_get_diff_wrapper,
    )

    registry.register_tool(
        name="internal_git_commit_and_push",
        description="Add all changes, commit them with a message, and push to the remote branch. Sets upstream tracking automatically.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "branch_name": {"type": "string", "description": "Branch to push to"},
                "commit_message": {"type": "string", "description": "Commit message"},
            },
            "required": ["repo_path", "branch_name", "commit_message"],
        },
        function=internal_git_commit_and_push_wrapper,
    )

    registry.register_tool(
        name="internal_git_get_commit_history",
        description="Get commit history for the repository. Shows recent commits with messages and hashes.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "max_commits": {
                    "type": "integer",
                    "description": "Maximum number of commits to retrieve (default: 10)",
                    "default": 10,
                },
                "branch": {
                    "type": "string",
                    "description": "Specific branch to get history for (optional, uses current branch if not specified)",
                },
            },
            "required": ["repo_path"],
        },
        function=internal_git_get_commit_history_wrapper,
    )

    registry.register_tool(
        name="internal_git_cherry_pick",
        description="Cherry-pick a specific commit to the current branch. Applies changes from one commit without merging entire branches.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "commit_hash": {"type": "string", "description": "Hash of the commit to cherry-pick"},
            },
            "required": ["repo_path", "commit_hash"],
        },
        function=internal_git_cherry_pick_wrapper,
    )

    registry.register_tool(
        name="internal_git_revert_commit",
        description="Revert a specific commit by creating a new revert commit. Safe way to undo changes while preserving history.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the local Git repository"},
                "commit_hash": {"type": "string", "description": "Hash of the commit to revert"},
            },
            "required": ["repo_path", "commit_hash"],
        },
        function=internal_git_revert_commit_wrapper,
    )

    logger.info("Registered 6 git commit tools")
