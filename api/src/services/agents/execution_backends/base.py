"""Base class for agent execution backends."""

from abc import ABC, abstractmethod


class BaseExecutionBackend(ABC):
    """Abstract base for agent task execution backends."""

    @abstractmethod
    async def dispatch(self, task_id: str, task_type: str, agent_id: str, tenant_id: str) -> str:
        """
        Dispatch a task for execution.

        Args:
            task_id: UUID of the ScheduledTask
            task_type: e.g. agent_task, autonomous_agent, database_query
            agent_id: UUID of the Agent
            tenant_id: UUID of the Tenant

        Returns:
            External job / invocation ID (empty string for no-op backends)
        """

    @abstractmethod
    def is_supported_task_type(self, task_type: str) -> bool:
        """Return True if this backend supports the given task type."""
