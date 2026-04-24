"""Celery tasks for A2A protocol async task execution."""

import asyncio
import logging

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.execute_a2a_task", soft_time_limit=3300, time_limit=3600)
def execute_a2a_task(self, task_db_id: str) -> dict:
    """
    Execute an A2A task asynchronously.

    Args:
        task_db_id: UUID string of the AgentA2ATask record (primary key)

    Returns:
        Dict with task_id and final status
    """
    logger.info(f"[A2A Celery] Executing task db_id={task_db_id}")

    async def _run():
        from src.services.agents.a2a_service import A2AService

        service = A2AService()
        await service.execute_task(task_db_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
        return {"task_db_id": task_db_id, "status": "executed"}
    except Exception as exc:
        logger.exception(f"[A2A Celery] Task {task_db_id} failed: {exc}")
        raise
    finally:
        loop.close()
