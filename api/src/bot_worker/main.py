"""Bot Worker entry point.

Run with: python -m src.bot_worker.main

Environment variables:
    WORKER_ID: Unique worker identifier (auto-generated if not set)
    BOT_WORKER_CAPACITY: Maximum bots per worker (default: 1000)
    BOT_WORKER_HEALTH_PORT: Health check server port (default: 8080)
    REDIS_URL: Redis connection URL
    DATABASE_URL: PostgreSQL connection URL
"""

import asyncio
import logging
import signal
import sys
from functools import partial

import redis

from .config import BotWorkerConfig
from .worker import BotWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# Reduce noise from third-party libraries
logging.getLogger("slack_sdk").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def shutdown(worker: BotWorker, sig: signal.Signals) -> None:
    """Handle graceful shutdown.

    Args:
        worker: BotWorker instance to shutdown
        sig: Signal that triggered shutdown
    """
    logger.info(f"Received {sig.name}, initiating graceful shutdown...")
    await worker.stop()


def handle_signal(worker: BotWorker, loop: asyncio.AbstractEventLoop, sig: signal.Signals) -> None:
    """Signal handler that schedules shutdown.

    Args:
        worker: BotWorker instance
        loop: Event loop
        sig: Signal received
    """
    loop.create_task(shutdown(worker, sig))


async def main() -> int:
    """Main entry point for the bot worker."""
    logger.info("=" * 60)
    logger.info("Starting Synkora Bot Worker")
    logger.info("=" * 60)

    # Load configuration
    config = BotWorkerConfig()
    logger.info(f"Worker ID: {config.worker_id}")
    logger.info(f"Capacity: {config.worker_capacity} bots")
    logger.info(f"Health port: {config.health_port}")

    # Connect to Redis
    from src.config.settings import settings

    redis_url = str(settings.redis_url)
    logger.info("Connecting to Redis...")

    try:
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            max_connections=10,
        )
        redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return 1

    # Initialize database
    from src.core.database import init_db

    init_db()
    logger.info("Database initialized")

    # Initialize encryption key
    from src.services.agents.security import set_encryption_key

    set_encryption_key(settings.encryption_key.encode())
    logger.info("Encryption key initialized")

    # Create worker
    worker = BotWorker(config, redis_client)

    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, partial(handle_signal, worker, loop, sig))

    # Start worker
    try:
        await worker.start()

        # Keep running until shutdown
        logger.info("Bot worker is running. Press Ctrl+C to stop.")
        while not worker.is_shutting_down:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Worker error: {e}")
        await worker.stop()
        return 1

    return 0


def run() -> None:
    """Entry point for the bot worker process."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
