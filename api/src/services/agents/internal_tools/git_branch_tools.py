"""
Git Branch Tools.

Handles branch lifecycle: creating, switching, listing, and pulling.
All operations work on a locally cloned repository within the agent workspace.
"""

import logging
import os
from typing import Any

from .git_helpers import _get_workspace_path, _run_git_command, _validate_repo_path

logger = logging.getLogger(__name__)


async def internal_git_create_branch(
    repo_path: str, branch_name: str, from_branch: str = "main", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Create a new branch in a local repository.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        branch_name: Name of the new branch to create
        from_branch: Branch to create from (default: "main")
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with success status and message.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        logger.info(f"Fetching latest changes in {repo_path}")
        fetch_result = _run_git_command(["git", "fetch", "origin"], repo_path)
        if not fetch_result["success"]:
            logger.warning(f"git fetch failed: {fetch_result['error']}")

        source_branch = f"origin/{from_branch}" if "/" not in from_branch else from_branch
        logger.info(f"Creating branch '{branch_name}' from '{source_branch}'")
        result = _run_git_command(["git", "checkout", "-b", branch_name, source_branch], repo_path)

        if not result["success"]:
            return {"success": False, "error": f"Failed to create branch: {result['error']}"}

        return {
            "success": True,
            "message": f"Successfully created branch '{branch_name}' from '{source_branch}'",
            "branch": branch_name,
        }

    except Exception as e:
        logger.error(f"Failed to create branch: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_switch_branch(
    repo_path: str, branch_name: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Switch to an existing branch in the repository.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        branch_name: Name of the branch to switch to
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with success status and message.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        result = _run_git_command(["git", "checkout", branch_name], repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to switch branch: {result['error']}"}

        return {"success": True, "message": f"Successfully switched to branch '{branch_name}'", "branch": branch_name}

    except Exception as e:
        logger.error(f"Failed to switch branch: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_list_branches(
    repo_path: str, include_remote: bool = False, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    List all branches in the repository.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        include_remote: Whether to include remote branches
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with success status and list of branches.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        command = ["git", "branch"]
        if include_remote:
            command.append("-a")

        result = _run_git_command(command, repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to list branches: {result['error']}"}

        branches = []
        current_branch = None

        for line in result["output"].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("*"):
                current_branch = line[2:].strip()
                branches.append(current_branch)
            else:
                branches.append(line.strip())

        return {
            "success": True,
            "branches": branches,
            "current_branch": current_branch,
            "total_branches": len(branches),
        }

    except Exception as e:
        logger.error(f"Failed to list branches: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_pull_changes(
    repo_path: str, remote: str = "origin", branch: str | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Pull changes from remote repository.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        remote: Remote name (default: "origin")
        branch: Branch name (if None, uses current branch)
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with success status and message.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        command = ["git", "pull", remote]
        if branch:
            command.append(branch)

        result = _run_git_command(command, repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to pull changes: {result['error']}"}

        return {
            "success": True,
            "message": f"Successfully pulled changes from {remote}" + (f"/{branch}" if branch else ""),
            "output": result["output"],
        }

    except Exception as e:
        logger.error(f"Failed to pull changes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
