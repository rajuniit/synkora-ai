"""
Git Commit Tools.

Handles working tree inspection and commit operations: status, diff,
commit history, commit-and-push, cherry-pick, and revert.
All operations work on a locally cloned repository within the agent workspace.
"""

import logging
import os
from typing import Any

from .git_helpers import _get_workspace_path, _run_git_command, _validate_repo_path

logger = logging.getLogger(__name__)


async def internal_git_get_status(repo_path: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Get the status of a Git repository (modified, staged, untracked files).

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with modified_files, staged_files, untracked_files, and has_changes.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        result = _run_git_command(["git", "status", "--porcelain"], repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to get status: {result['error']}"}

        modified_files = []
        staged_files = []
        untracked_files = []

        for line in result["output"].split("\n"):
            if not line.strip():
                continue
            status = line[:2]
            filename = line[3:]

            if status[0] == "M":
                staged_files.append(filename)
            elif status[1] == "M":
                modified_files.append(filename)
            elif status == "??":
                untracked_files.append(filename)
            elif status[0] == "A":
                staged_files.append(filename)

        return {
            "success": True,
            "modified_files": modified_files,
            "staged_files": staged_files,
            "untracked_files": untracked_files,
            "has_changes": bool(modified_files or staged_files or untracked_files),
            "raw_output": result["output"],
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_get_diff(
    repo_path: str, file_path: str | None = None, staged: bool = False, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get diff of local working tree changes in a cloned repository.

    Use this after cloning a repo with internal_git_clone_repo to inspect
    local changes before committing. For viewing a GitHub PR's diff without
    cloning, use internal_github_get_pr_diff instead.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        file_path: Specific file to get diff for (optional)
        staged: Get staged changes instead of working directory changes
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with diff output and has_changes flag.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        command = ["git", "diff"]
        if staged:
            command.append("--cached")
        if file_path:
            command.append(file_path)

        result = _run_git_command(command, repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to get diff: {result['error']}"}

        return {
            "success": True,
            "diff": result["output"],
            "has_changes": bool(result["output"].strip()),
            "file_path": file_path,
            "staged": staged,
        }

    except Exception as e:
        logger.error(f"Failed to get diff: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_get_commit_history(
    repo_path: str, max_commits: int = 10, branch: str | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get commit history for the repository.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        max_commits: Maximum number of commits to retrieve
        branch: Specific branch to get history for (optional)
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with commits list and total_commits count.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        command = ["git", "log", f"--max-count={max_commits}", "--oneline", "--decorate"]
        if branch:
            command.append(branch)

        result = _run_git_command(command, repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to get commit history: {result['error']}"}

        commits = []
        for line in result["output"].split("\n"):
            if line.strip():
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    commits.append({"hash": parts[0], "message": parts[1]})

        return {"success": True, "commits": commits, "total_commits": len(commits), "branch": branch}

    except Exception as e:
        logger.error(f"Failed to get commit history: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_commit_and_push(
    repo_path: str, branch_name: str, commit_message: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Add all changes, commit them, and push to remote branch.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        branch_name: Branch to push to
        commit_message: Commit message
        config: Configuration dictionary containing workspace_path

    Returns:
        Dictionary with success status and push details.
    """
    try:
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_repo_path(repo_path, workspace_path)
        if not is_valid:
            return {"success": False, "error": error}

        if not os.path.exists(repo_path):
            return {"success": False, "error": f"Repository path does not exist: {repo_path}"}

        # Configure git user identity if not already set (required in container environments)
        git_email = os.getenv("GIT_AGENT_EMAIL", "agent@localhost")
        git_name = os.getenv("GIT_AGENT_NAME", "AI Agent")
        _run_git_command(["git", "config", "user.email", git_email], repo_path)
        _run_git_command(["git", "config", "user.name", git_name], repo_path)

        logger.info(f"Adding all changes in {repo_path}")
        add_result = _run_git_command(["git", "add", "."], repo_path)
        if not add_result["success"]:
            return {"success": False, "error": f"Failed to add files: {add_result['error']}"}

        logger.info(f"Committing changes with message: '{commit_message}'")
        commit_result = _run_git_command(["git", "commit", "-m", commit_message], repo_path)
        if not commit_result["success"]:
            if "nothing to commit" in commit_result["output"].lower():
                logger.info("No changes to commit")
                return {"success": True, "message": "No changes to commit", "committed": False}
            return {"success": False, "error": f"Failed to commit: {commit_result['error']}"}

        logger.info(f"Pushing to origin/{branch_name}")
        push_result = _run_git_command(["git", "push", "--set-upstream", "origin", branch_name], repo_path)
        if not push_result["success"]:
            return {"success": False, "error": f"Failed to push: {push_result['error']}", "committed": True}

        return {
            "success": True,
            "message": f"Successfully committed and pushed changes to '{branch_name}'",
            "committed": True,
            "pushed": True,
            "branch": branch_name,
        }

    except Exception as e:
        logger.error(f"Failed to commit and push: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_cherry_pick(
    repo_path: str, commit_hash: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Cherry-pick a specific commit to the current branch.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        commit_hash: Hash of the commit to cherry-pick
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

        result = _run_git_command(["git", "cherry-pick", commit_hash], repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to cherry-pick commit: {result['error']}"}

        return {
            "success": True,
            "message": f"Successfully cherry-picked commit {commit_hash}",
            "commit_hash": commit_hash,
        }

    except Exception as e:
        logger.error(f"Failed to cherry-pick commit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def internal_git_revert_commit(
    repo_path: str, commit_hash: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Revert a specific commit by creating a new revert commit.

    Args:
        repo_path: Path to the local Git repository (must be within workspace)
        commit_hash: Hash of the commit to revert
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

        result = _run_git_command(["git", "revert", "--no-edit", commit_hash], repo_path)
        if not result["success"]:
            return {"success": False, "error": f"Failed to revert commit: {result['error']}"}

        return {"success": True, "message": f"Successfully reverted commit {commit_hash}", "commit_hash": commit_hash}

    except Exception as e:
        logger.error(f"Failed to revert commit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
