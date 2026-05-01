"""Celery execution backend (default — no-op dispatch)."""

from .base import BaseExecutionBackend


class CeleryBackend(BaseExecutionBackend):
    """
    Default backend.  Celery already owns the task at this point, so
    dispatch() is a no-op and returns an empty string.
    """

    async def dispatch(self, task_id: str, task_type: str, agent_id: str, tenant_id: str) -> str:
        return ""

    def is_supported_task_type(self, task_type: str) -> bool:
        return True
