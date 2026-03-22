"""
Scheduler tools for agents to create and manage scheduled tasks.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ....services.scheduler.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


async def internal_create_scheduled_task(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    task_type: str,
    interval_seconds: int,
    config: dict[str, Any],
    description: str | None = None,
    is_active: bool = True,
    **context,
) -> dict[str, Any]:
    """
    Create a scheduled task using interval-based scheduling.

    Args:
        db: Database session
        tenant_id: Tenant ID
        name: Task name
        task_type: Type of task (e.g., 'followup_reminder', 'agent_task')
        interval_seconds: Interval in seconds between task executions
        config: Task configuration dictionary
        description: Optional description
        is_active: Whether task is active
        **context: Additional context from runtime

    Returns:
        Dictionary with task details

    Common intervals (minimum 60 seconds):
    - Every 1 minute: 60
    - Every 2 minutes: 120
    - Every 5 minutes: 300
    - Every 10 minutes: 600
    - Every 15 minutes: 900
    - Every 30 minutes: 1800
    - Every hour: 3600
    - Every 6 hours: 21600
    - Every day: 86400
    - Every week: 604800
    """
    try:
        # Convert interval_seconds to int (LLM may pass as string)
        interval_seconds = int(interval_seconds)

        scheduler_service = SchedulerService(db)

        # Get account ID from context
        account_id = context.get("account_id")
        if not account_id:
            return {"success": False, "error": "Account ID not found in context"}

        # Use create_agent_task with interval-based scheduling
        task = await scheduler_service.create_agent_task(
            tenant_id=UUID(tenant_id),
            name=name,
            task_type=task_type,
            interval_seconds=interval_seconds,
            created_by=UUID(account_id),
            config=config,
            description=description,
            is_active=is_active,
        )

        logger.info(f"Created scheduled task {task.id}: {name}")

        # Format interval for display
        if interval_seconds >= 86400:
            interval_display = f"every {interval_seconds // 86400} day(s)"
        elif interval_seconds >= 3600:
            interval_display = f"every {interval_seconds // 3600} hour(s)"
        elif interval_seconds >= 60:
            interval_display = f"every {interval_seconds // 60} minute(s)"
        else:
            interval_display = f"every {interval_seconds} second(s)"

        return {
            "success": True,
            "task_id": str(task.id),
            "name": task.name,
            "interval_seconds": task.interval_seconds,
            "is_active": task.is_active,
            "message": f"Scheduled task '{name}' created successfully. It will run {interval_display}.",
        }

    except Exception as e:
        logger.error(f"Error creating scheduled task: {str(e)}")
        return {"success": False, "error": str(e)}


async def internal_create_cron_scheduled_task(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    task_type: str,
    cron_expression: str,
    config: dict[str, Any],
    description: str | None = None,
    is_active: bool = True,
    **context,
) -> dict[str, Any]:
    """
    Create a scheduled task using cron expression for precise timing.

    Use this for tasks that need to run at specific times (e.g., 7 AM daily).

    Args:
        db: Database session
        tenant_id: Tenant ID
        name: Task name
        task_type: Type of task (e.g., 'agent_task', 'report')
        cron_expression: Cron expression for scheduling (e.g., '0 7 * * *' for 7 AM daily)
        config: Task configuration dictionary
        description: Optional description
        is_active: Whether task is active
        **context: Additional context from runtime

    Returns:
        Dictionary with task details

    Common cron expressions:
    - '0 7 * * *' = Every day at 7:00 AM
    - '0 9 * * 1-5' = Weekdays at 9:00 AM
    - '0 */2 * * *' = Every 2 hours
    - '30 8 * * *' = Every day at 8:30 AM
    - '0 0 * * 0' = Every Sunday at midnight
    - '0 18 * * 5' = Every Friday at 6:00 PM

    Cron format: minute hour day-of-month month day-of-week
    - minute: 0-59
    - hour: 0-23
    - day-of-month: 1-31
    - month: 1-12
    - day-of-week: 0-6 (Sunday=0)
    """
    try:
        scheduler_service = SchedulerService(db)

        # Get account ID from context
        account_id = context.get("account_id")
        if not account_id:
            return {"success": False, "error": "Account ID not found in context"}

        # Use create_task with cron-based scheduling
        task = await scheduler_service.create_task(
            tenant_id=UUID(tenant_id),
            name=name,
            task_type=task_type,
            schedule=cron_expression,
            created_by=UUID(account_id),
            chart_config=config,
            description=description,
            is_active=is_active,
        )

        logger.info(f"Created cron scheduled task {task.id}: {name} with schedule {cron_expression}")

        # Get human-readable description
        validation = scheduler_service.validate_cron(cron_expression)
        schedule_description = validation.get("description", cron_expression)

        return {
            "success": True,
            "task_id": str(task.id),
            "name": task.name,
            "cron_expression": task.cron_expression,
            "schedule_description": schedule_description,
            "is_active": task.is_active,
            "next_runs": validation.get("next_runs", [])[:3],
            "message": f"Scheduled task '{name}' created successfully. Schedule: {schedule_description}",
        }

    except ValueError as e:
        logger.error(f"Invalid cron expression: {str(e)}")
        return {"success": False, "error": f"Invalid cron expression: {str(e)}"}
    except Exception as e:
        logger.error(f"Error creating cron scheduled task: {str(e)}")
        return {"success": False, "error": str(e)}


async def internal_list_scheduled_tasks(db: AsyncSession, tenant_id: str, **context) -> dict[str, Any]:
    """
    List all scheduled tasks for the tenant.

    Args:
        db: Database session
        tenant_id: Tenant ID
        **context: Additional context from runtime

    Returns:
        Dictionary with list of tasks
    """
    try:
        scheduler_service = SchedulerService(db)

        tasks = await scheduler_service.list_tasks(tenant_id=UUID(tenant_id), skip=0, limit=100)

        task_list = []
        for task in tasks:
            task_list.append(
                {
                    "task_id": str(task.id),
                    "name": task.name,
                    "task_type": task.task_type,
                    "interval_seconds": task.interval_seconds,
                    "is_active": task.is_active,
                    "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                    "created_at": task.created_at.isoformat(),
                }
            )

        return {"success": True, "count": len(task_list), "tasks": task_list}

    except Exception as e:
        logger.error(f"Error listing scheduled tasks: {str(e)}")
        return {"success": False, "error": str(e)}


async def internal_delete_scheduled_task(db: AsyncSession, task_id: str, **context) -> dict[str, Any]:
    """
    Delete a scheduled task.

    Args:
        db: Database session
        task_id: Task ID to delete
        **context: Additional context from runtime

    Returns:
        Dictionary with deletion result
    """
    try:
        scheduler_service = SchedulerService(db)

        await scheduler_service.delete_task(UUID(task_id))

        logger.info(f"Deleted scheduled task {task_id}")

        return {"success": True, "message": "Scheduled task deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting scheduled task: {str(e)}")
        return {"success": False, "error": str(e)}


async def internal_toggle_scheduled_task(db: AsyncSession, task_id: str, **context) -> dict[str, Any]:
    """
    Toggle a scheduled task's active status.

    Args:
        db: Database session
        task_id: Task ID to toggle
        **context: Additional context from runtime

    Returns:
        Dictionary with toggle result
    """
    try:
        scheduler_service = SchedulerService(db)

        task = await scheduler_service.toggle_task(UUID(task_id))

        status = "activated" if task.is_active else "deactivated"
        logger.info(f"Toggled scheduled task {task_id} to {status}")

        return {
            "success": True,
            "task_id": str(task.id),
            "is_active": task.is_active,
            "message": f"Task {status} successfully",
        }

    except Exception as e:
        logger.error(f"Error toggling scheduled task: {str(e)}")
        return {"success": False, "error": str(e)}
