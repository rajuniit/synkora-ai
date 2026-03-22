"""Bot Worker service module.

Provides services for managing bot workers and triggering bot lifecycle events.
"""

from .bot_deployment_service import BotDeploymentService
from .worker_registry import WorkerRegistry

__all__ = [
    "BotDeploymentService",
    "WorkerRegistry",
]
