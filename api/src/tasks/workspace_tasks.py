"""
Celery tasks for workspace management.

Provides scheduled cleanup of expired workspaces and tenant-specific cleanup.
"""

import logging
import uuid

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.cleanup_expired_workspaces", bind=True)
def cleanup_expired_workspaces(self, ttl_hours: int = 24) -> dict:
    """
    Clean up all workspaces that have exceeded their TTL.

    This task runs periodically to remove stale workspace directories,
    freeing up disk space on the server.

    Args:
        ttl_hours: Time-to-live in hours for workspaces (default: 24)

    Returns:
        Dictionary with cleanup statistics:
        - cleaned: Number of workspaces removed
        - failed: Number of cleanup failures
        - total_size_mb: Total disk space freed in MB
    """
    logger.info(f"Starting workspace cleanup with TTL of {ttl_hours} hours")

    try:
        from src.services.agents.workspace_manager import WorkspaceManager

        manager = WorkspaceManager()
        result = manager.cleanup_expired_workspaces(ttl_hours=ttl_hours)

        logger.info(
            f"Workspace cleanup complete: {result['cleaned']} cleaned, "
            f"{result['failed']} failed, {result['total_size_mb']}MB freed"
        )

        return {
            "success": True,
            "cleaned": result["cleaned"],
            "failed": result["failed"],
            "total_size_mb": result["total_size_mb"],
        }

    except Exception as e:
        logger.error(f"Workspace cleanup task failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "cleaned": 0,
            "failed": 0,
            "total_size_mb": 0,
        }


@celery_app.task(name="tasks.cleanup_tenant_workspaces", bind=True)
def cleanup_tenant_workspaces(self, tenant_id: str) -> dict:
    """
    Clean up all workspaces for a specific tenant.

    This task can be called when a tenant is deleted or when
    manual cleanup is needed.

    Args:
        tenant_id: UUID of the tenant (as string)

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info(f"Starting workspace cleanup for tenant {tenant_id}")

    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError as e:
        logger.error(f"Invalid tenant_id format: {tenant_id}")
        return {
            "success": False,
            "error": f"Invalid tenant_id format: {e}",
            "cleaned": 0,
            "failed": 0,
            "total_size_mb": 0,
        }

    try:
        from src.services.agents.workspace_manager import WorkspaceManager

        manager = WorkspaceManager()
        result = manager.cleanup_tenant_workspaces(tenant_uuid)

        logger.info(
            f"Tenant workspace cleanup complete for {tenant_id}: "
            f"{result['cleaned']} cleaned, {result['failed']} failed, "
            f"{result['total_size_mb']}MB freed"
        )

        return {
            "success": True,
            "tenant_id": tenant_id,
            "cleaned": result["cleaned"],
            "failed": result["failed"],
            "total_size_mb": result["total_size_mb"],
        }

    except Exception as e:
        logger.error(f"Tenant workspace cleanup failed for {tenant_id}: {e}", exc_info=True)
        return {
            "success": False,
            "tenant_id": tenant_id,
            "error": str(e),
            "cleaned": 0,
            "failed": 0,
            "total_size_mb": 0,
        }


@celery_app.task(name="tasks.cleanup_session_workspace", bind=True)
def cleanup_session_workspace(self, tenant_id: str, session_id: str) -> dict:
    """
    Clean up a specific session's workspace.

    Can be called when a conversation ends or times out.

    Args:
        tenant_id: UUID of the tenant (as string)
        session_id: UUID of the session/conversation (as string)

    Returns:
        Dictionary with cleanup result
    """
    logger.info(f"Cleaning up workspace for tenant {tenant_id}, session {session_id}")

    try:
        tenant_uuid = uuid.UUID(tenant_id)
        session_uuid = uuid.UUID(session_id)
    except ValueError as e:
        logger.error(f"Invalid UUID format: {e}")
        return {
            "success": False,
            "error": f"Invalid UUID format: {e}",
        }

    try:
        from src.services.agents.workspace_manager import WorkspaceManager

        manager = WorkspaceManager()
        workspace_path = manager.get_or_create_workspace(tenant_uuid, session_uuid)

        # Get info before cleanup
        info = manager.get_workspace_info(workspace_path)
        size_mb = info["size_mb"] if info else 0

        # Perform cleanup
        success = manager.cleanup_workspace(workspace_path)

        return {
            "success": success,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "size_mb": size_mb,
        }

    except Exception as e:
        logger.error(f"Session workspace cleanup failed: {e}", exc_info=True)
        return {
            "success": False,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "error": str(e),
        }
