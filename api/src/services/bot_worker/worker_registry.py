"""Worker Registry - tracks and manages bot workers.

Provides functionality to:
- List all registered workers
- Get worker health status
- Identify dead workers
- Trigger rebalancing
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import redis

from ...bot_worker.redis_state import BotRedisState, WorkerInfo

logger = logging.getLogger(__name__)


@dataclass
class WorkerStatus:
    """Worker status with health information."""

    worker_id: str
    capacity: int
    active_bots: int
    started_at: float
    last_heartbeat: float
    is_healthy: bool
    utilization_percent: float
    host: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "capacity": self.capacity,
            "active_bots": self.active_bots,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "is_healthy": self.is_healthy,
            "utilization_percent": round(self.utilization_percent, 2),
            "host": self.host,
        }


class WorkerRegistry:
    """Registry for tracking and managing bot workers."""

    def __init__(self, redis_client: redis.Redis, heartbeat_timeout: int = 30):
        """Initialize the worker registry.

        Args:
            redis_client: Connected Redis client
            heartbeat_timeout: Seconds before a worker is considered dead
        """
        self.redis_state = BotRedisState(redis_client)
        self.heartbeat_timeout = heartbeat_timeout

    def get_all_workers(self) -> list[WorkerStatus]:
        """Get status of all registered workers.

        Returns:
            List of WorkerStatus for all workers
        """
        now = time.time()
        workers = self.redis_state.get_all_workers()

        return [
            WorkerStatus(
                worker_id=w.worker_id,
                capacity=w.capacity,
                active_bots=w.active_bots,
                started_at=w.started_at,
                last_heartbeat=w.last_heartbeat,
                is_healthy=(now - w.last_heartbeat) < self.heartbeat_timeout,
                utilization_percent=(w.active_bots / w.capacity * 100) if w.capacity > 0 else 0,
                host=w.host,
            )
            for w in workers
        ]

    def get_worker(self, worker_id: str) -> WorkerStatus | None:
        """Get status of a specific worker.

        Args:
            worker_id: Worker to look up

        Returns:
            WorkerStatus if found, None otherwise
        """
        info = self.redis_state.get_worker_info(worker_id)
        if not info:
            return None

        now = time.time()
        return WorkerStatus(
            worker_id=info.worker_id,
            capacity=info.capacity,
            active_bots=info.active_bots,
            started_at=info.started_at,
            last_heartbeat=info.last_heartbeat,
            is_healthy=(now - info.last_heartbeat) < self.heartbeat_timeout,
            utilization_percent=(info.active_bots / info.capacity * 100) if info.capacity > 0 else 0,
            host=info.host,
        )

    def get_healthy_worker_count(self) -> int:
        """Get the number of healthy workers.

        Returns:
            Count of healthy workers
        """
        healthy = self.redis_state.get_healthy_workers(self.heartbeat_timeout)
        return len(healthy)

    def get_total_capacity(self) -> dict[str, int]:
        """Get total capacity across all healthy workers.

        Returns:
            Dict with total_capacity, active_bots, available_capacity
        """
        workers = self.get_all_workers()
        healthy_workers = [w for w in workers if w.is_healthy]

        total_capacity = sum(w.capacity for w in healthy_workers)
        active_bots = sum(w.active_bots for w in healthy_workers)

        return {
            "total_capacity": total_capacity,
            "active_bots": active_bots,
            "available_capacity": total_capacity - active_bots,
            "healthy_workers": len(healthy_workers),
            "total_workers": len(workers),
        }

    def get_bots_for_worker(self, worker_id: str) -> list[dict[str, str]]:
        """Get all bots assigned to a worker.

        Args:
            worker_id: Worker to look up

        Returns:
            List of bot info dicts with bot_id and bot_type
        """
        bots = self.redis_state.get_bots_for_worker(worker_id)
        return [{"bot_id": bot_id, "bot_type": bot_type.value} for bot_id, bot_type in bots]

    def cleanup_dead_workers(self) -> list[str]:
        """Remove dead workers from the registry.

        Returns:
            List of removed worker IDs
        """
        dead_workers = self.redis_state.get_dead_workers(self.heartbeat_timeout)

        for worker_id in dead_workers:
            self.redis_state.unregister_worker(worker_id)
            logger.info(f"Removed dead worker: {worker_id}")

        return dead_workers
