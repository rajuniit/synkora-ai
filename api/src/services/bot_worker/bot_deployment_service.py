"""Bot Deployment Service - manages bot lifecycle through worker pool.

Provides high-level operations for:
- Starting/stopping bots via Redis events
- Checking bot deployment status
- Getting bot assignment information
"""

import logging
import time
from typing import Any
from uuid import UUID

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...bot_worker.consistent_hash import ConsistentHash
from ...bot_worker.redis_state import BotEvent, BotEventType, BotRedisState, BotType
from ...models.slack_bot import SlackBot
from ...models.telegram_bot import TelegramBot
from ...models.whatsapp_bot import WhatsAppBot

logger = logging.getLogger(__name__)


class BotDeploymentService:
    """Service for managing bot deployments through the worker pool."""

    def __init__(self, db: AsyncSession, redis_client: redis.Redis, heartbeat_timeout: int = 30):
        """Initialize the bot deployment service.

        Args:
            db: Database session
            redis_client: Connected Redis client
            heartbeat_timeout: Seconds before a worker is considered dead
        """
        self.db = db
        self.redis_state = BotRedisState(redis_client)
        self.heartbeat_timeout = heartbeat_timeout

    def activate_bot(self, bot_id: str, bot_type: BotType) -> dict[str, Any]:
        """Activate a bot by publishing an event to the worker pool.

        Args:
            bot_id: Bot to activate
            bot_type: Type of bot (slack/telegram)

        Returns:
            Dict with status and assigned worker info
        """
        # Get healthy workers
        healthy_workers = self.redis_state.get_healthy_workers(self.heartbeat_timeout)
        if not healthy_workers:
            logger.error("No healthy workers available to handle bot")
            return {
                "success": False,
                "error": "No healthy workers available",
                "bot_id": bot_id,
            }

        # Determine which worker will handle this bot via consistent hashing
        hash_ring = ConsistentHash(nodes=healthy_workers)
        assigned_worker = hash_ring.get_node(bot_id)

        # Publish activation event
        event = BotEvent(
            event_type=BotEventType.ACTIVATE,
            bot_id=bot_id,
            bot_type=bot_type,
            timestamp=time.time(),
        )
        event_id = self.redis_state.publish_bot_event(event)

        logger.info(f"Published activate event for {bot_type.value} bot {bot_id}, assigned to {assigned_worker}")

        return {
            "success": True,
            "bot_id": bot_id,
            "bot_type": bot_type.value,
            "assigned_worker": assigned_worker,
            "event_id": event_id,
        }

    def deactivate_bot(self, bot_id: str, bot_type: BotType) -> dict[str, Any]:
        """Deactivate a bot by publishing an event to the worker pool.

        Args:
            bot_id: Bot to deactivate
            bot_type: Type of bot (slack/telegram)

        Returns:
            Dict with status info
        """
        # Check current assignment
        assignment = self.redis_state.get_bot_assignment(bot_id)

        if assignment:
            worker_id, _ = assignment
            # Send direct command to the assigned worker for faster response
            self.redis_state.send_worker_command(
                worker_id,
                {"action": "stop_bot", "bot_id": bot_id},
            )
            logger.info(f"Sent stop command to worker {worker_id} for bot {bot_id}")
        else:
            # Publish deactivation event (worker will ignore if not managing this bot)
            event = BotEvent(
                event_type=BotEventType.DEACTIVATE,
                bot_id=bot_id,
                bot_type=bot_type,
                timestamp=time.time(),
            )
            self.redis_state.publish_bot_event(event)
            logger.info(f"Published deactivate event for bot {bot_id}")

        return {
            "success": True,
            "bot_id": bot_id,
            "bot_type": bot_type.value,
        }

    def restart_bot(self, bot_id: str, bot_type: BotType) -> dict[str, Any]:
        """Restart a bot by publishing a restart event.

        Args:
            bot_id: Bot to restart
            bot_type: Type of bot (slack/telegram)

        Returns:
            Dict with status info
        """
        # Check current assignment
        assignment = self.redis_state.get_bot_assignment(bot_id)

        if assignment:
            worker_id, _ = assignment
            # Send direct command to the assigned worker
            self.redis_state.send_worker_command(
                worker_id,
                {"action": "restart_bot", "bot_id": bot_id},
            )
            logger.info(f"Sent restart command to worker {worker_id} for bot {bot_id}")
        else:
            # Publish restart event
            event = BotEvent(
                event_type=BotEventType.RESTART,
                bot_id=bot_id,
                bot_type=bot_type,
                timestamp=time.time(),
            )
            self.redis_state.publish_bot_event(event)
            logger.info(f"Published restart event for bot {bot_id}")

        return {
            "success": True,
            "bot_id": bot_id,
            "bot_type": bot_type.value,
        }

    def get_bot_status(self, bot_id: str) -> dict[str, Any]:
        """Get deployment status of a bot.

        Args:
            bot_id: Bot to check

        Returns:
            Dict with deployment status info
        """
        assignment = self.redis_state.get_bot_assignment(bot_id)

        if not assignment:
            return {
                "bot_id": bot_id,
                "is_deployed": False,
                "assigned_worker": None,
                "bot_type": None,
            }

        worker_id, bot_type = assignment

        # Check if the worker is still healthy
        worker_info = self.redis_state.get_worker_info(worker_id)
        is_worker_healthy = False
        if worker_info:
            is_worker_healthy = (time.time() - worker_info.last_heartbeat) < self.heartbeat_timeout

        return {
            "bot_id": bot_id,
            "is_deployed": True,
            "assigned_worker": worker_id,
            "bot_type": bot_type.value,
            "worker_healthy": is_worker_healthy,
        }

    async def activate_slack_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Convenience method to activate a Slack bot.

        Args:
            bot_id: Slack bot UUID

        Returns:
            Activation result
        """
        # Update database status
        result = await self.db.execute(select(SlackBot).filter(SlackBot.id == bot_id))
        slack_bot = result.scalar_one_or_none()
        if not slack_bot:
            return {"success": False, "error": "Slack bot not found"}

        slack_bot.is_active = True
        await self.db.commit()

        return self.activate_bot(str(bot_id), BotType.SLACK)

    async def deactivate_slack_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Convenience method to deactivate a Slack bot.

        Args:
            bot_id: Slack bot UUID

        Returns:
            Deactivation result
        """
        # Update database status
        result = await self.db.execute(select(SlackBot).filter(SlackBot.id == bot_id))
        slack_bot = result.scalar_one_or_none()
        if not slack_bot:
            return {"success": False, "error": "Slack bot not found"}

        slack_bot.is_active = False
        slack_bot.connection_status = "disconnected"
        slack_bot.assigned_worker_id = None
        await self.db.commit()

        return self.deactivate_bot(str(bot_id), BotType.SLACK)

    async def activate_telegram_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Convenience method to activate a Telegram bot.

        Args:
            bot_id: Telegram bot UUID

        Returns:
            Activation result
        """
        # Update database status
        result = await self.db.execute(select(TelegramBot).filter(TelegramBot.id == bot_id))
        telegram_bot = result.scalar_one_or_none()
        if not telegram_bot:
            return {"success": False, "error": "Telegram bot not found"}

        telegram_bot.is_active = True
        await self.db.commit()

        return self.activate_bot(str(bot_id), BotType.TELEGRAM)

    async def deactivate_telegram_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Convenience method to deactivate a Telegram bot.

        Args:
            bot_id: Telegram bot UUID

        Returns:
            Deactivation result
        """
        # Update database status
        result = await self.db.execute(select(TelegramBot).filter(TelegramBot.id == bot_id))
        telegram_bot = result.scalar_one_or_none()
        if not telegram_bot:
            return {"success": False, "error": "Telegram bot not found"}

        telegram_bot.is_active = False
        telegram_bot.connection_status = "disconnected"
        telegram_bot.assigned_worker_id = None
        await self.db.commit()

        return self.deactivate_bot(str(bot_id), BotType.TELEGRAM)

    async def activate_whatsapp_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Activate a WhatsApp device-link bot through the worker pool."""
        result = await self.db.execute(select(WhatsAppBot).filter(WhatsAppBot.id == bot_id))
        whatsapp_bot = result.scalar_one_or_none()
        if not whatsapp_bot:
            return {"success": False, "error": "WhatsApp bot not found"}

        whatsapp_bot.is_active = True
        await self.db.commit()

        return self.activate_bot(str(bot_id), BotType.WHATSAPP)

    async def deactivate_whatsapp_bot(self, bot_id: UUID) -> dict[str, Any]:
        """Deactivate a WhatsApp device-link bot through the worker pool."""
        result = await self.db.execute(select(WhatsAppBot).filter(WhatsAppBot.id == bot_id))
        whatsapp_bot = result.scalar_one_or_none()
        if not whatsapp_bot:
            return {"success": False, "error": "WhatsApp bot not found"}

        whatsapp_bot.is_active = False
        whatsapp_bot.connection_status = "disconnected"
        await self.db.commit()

        return self.deactivate_bot(str(bot_id), BotType.WHATSAPP)
