"""Bot Worker module for scalable bot connection management.

This module provides a worker pool architecture for managing Slack and Telegram
bot connections at scale. Instead of running bots in the API process, bots are
distributed across multiple worker processes using consistent hashing.

Key components:
- BotWorker: Main worker class that manages multiple bot connections
- ConsistentHash: Deterministic bot-to-worker assignment
- RedisState: Distributed state management via Redis
- HealthServer: HTTP health check endpoint
"""

from .config import BotWorkerConfig
from .consistent_hash import ConsistentHash
from .redis_state import BotRedisState
from .worker import BotWorker

__all__ = [
    "BotWorker",
    "BotWorkerConfig",
    "ConsistentHash",
    "BotRedisState",
]
