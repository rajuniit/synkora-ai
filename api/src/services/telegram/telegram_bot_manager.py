"""Telegram Bot Manager for managing bot lifecycle and operations."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.redis import get_redis
from ...models.agent import Agent
from ...models.telegram_bot import TelegramBot
from ...services.agents.security import encrypt_value
from ...services.bot_worker.bot_deployment_service import BotDeploymentService
from ...services.oauth.telegram_auth import TelegramAuth
from .telegram_webhook_service import TelegramWebhookService

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """Manager for Telegram bot operations."""

    def __init__(self, db_session: AsyncSession, webhook_base_url: str | None = None):
        self.db_session = db_session
        # Use bot deployment service for worker pool (polling bots)
        redis_client = get_redis()
        self.deployment_service = BotDeploymentService(db_session, redis_client)
        # Keep webhook service for webhook-mode bots (handled by API, not workers)
        self.webhook_service = TelegramWebhookService(db_session)
        self.webhook_base_url = webhook_base_url

    async def create_bot(
        self,
        agent_id: UUID,
        tenant_id: UUID,
        bot_name: str,
        bot_token: str,
        use_webhook: bool = False,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        created_by: UUID | None = None,
    ) -> TelegramBot:
        """
        Create a new Telegram bot configuration.

        Args:
            agent_id: ID of the agent to connect
            tenant_id: ID of the tenant
            bot_name: Display name for the bot
            bot_token: Bot token from BotFather
            use_webhook: Whether to use webhook instead of long polling
            webhook_url: Webhook URL if use_webhook is true
            webhook_secret: Secret for webhook validation

        Returns:
            TelegramBot: Created bot instance
        """
        try:
            # Validate the token first
            validation_result = await TelegramAuth.validate_token(bot_token)
            if not validation_result["success"]:
                raise ValueError(f"Invalid bot token: {validation_result.get('error', 'Unknown error')}")

            # Encrypt token
            encrypted_token = encrypt_value(bot_token)
            encrypted_webhook_secret = encrypt_value(webhook_secret) if webhook_secret else None

            # Create bot with info from validation
            telegram_bot = TelegramBot(
                agent_id=agent_id,
                tenant_id=tenant_id,
                bot_name=bot_name,
                bot_username=validation_result.get("bot_username"),
                bot_token=encrypted_token,
                telegram_bot_id=validation_result.get("bot_id"),
                use_webhook=use_webhook,
                webhook_url=webhook_url,
                webhook_secret=encrypted_webhook_secret,
                is_active=True,
                connection_status="disconnected",
                created_by=created_by,
            )

            self.db_session.add(telegram_bot)
            await self.db_session.commit()
            await self.db_session.refresh(telegram_bot)

            logger.info(f"Created Telegram bot {bot_name} (@{telegram_bot.bot_username}, ID: {telegram_bot.id})")
            return telegram_bot

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to create Telegram bot: {str(e)}")
            raise

    async def update_bot(
        self,
        bot_id: UUID,
        bot_name: str | None = None,
        bot_token: str | None = None,
        use_webhook: bool | None = None,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        is_active: bool | None = None,
    ) -> TelegramBot:
        """
        Update Telegram bot configuration.

        Args:
            bot_id: ID of the bot to update
            bot_name: New display name (optional)
            bot_token: New bot token (optional)
            use_webhook: Whether to use webhook (optional)
            webhook_url: New webhook URL (optional)
            webhook_secret: New webhook secret (optional)
            is_active: New active status (optional)

        Returns:
            TelegramBot: Updated bot instance
        """
        try:
            telegram_bot = await self.db_session.get(TelegramBot, bot_id)
            if not telegram_bot:
                raise ValueError(f"Telegram bot {bot_id} not found")

            # Track if bot was running before update
            was_running = telegram_bot.connection_status == "connected"
            token_updated = bot_token is not None

            # Stop bot if running and token is being updated
            if token_updated and was_running:
                logger.info(f"Stopping bot {bot_id} for token update")
                await self.deployment_service.deactivate_telegram_bot(bot_id)
                import asyncio

                await asyncio.sleep(1)

            # Validate new token if provided
            if bot_token:
                validation_result = await TelegramAuth.validate_token(bot_token)
                if not validation_result["success"]:
                    raise ValueError(f"Invalid bot token: {validation_result.get('error', 'Unknown error')}")

                telegram_bot.bot_token = encrypt_value(bot_token)
                telegram_bot.bot_username = validation_result.get("bot_username")
                telegram_bot.telegram_bot_id = validation_result.get("bot_id")

            # Update other fields
            if bot_name is not None:
                telegram_bot.bot_name = bot_name

            if use_webhook is not None:
                telegram_bot.use_webhook = use_webhook

            if webhook_url is not None:
                telegram_bot.webhook_url = webhook_url

            if webhook_secret is not None:
                telegram_bot.webhook_secret = encrypt_value(webhook_secret)

            if is_active is not None:
                telegram_bot.is_active = is_active
                if not is_active and telegram_bot.connection_status == "connected":
                    await self.deployment_service.deactivate_telegram_bot(bot_id)

            telegram_bot.updated_at = datetime.now(UTC)
            await self.db_session.commit()
            await self.db_session.refresh(telegram_bot)

            # Restart bot if it was running and token was updated
            if token_updated and was_running and telegram_bot.is_active:
                logger.info(f"Restarting bot {bot_id} with new token")
                import asyncio

                await asyncio.sleep(1)
                await self.start_bot(bot_id)

            logger.info(f"Updated Telegram bot {bot_id}")
            return telegram_bot

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to update Telegram bot {bot_id}: {str(e)}")
            raise

    async def delete_bot(self, bot_id: UUID) -> bool:
        """
        Delete a Telegram bot (soft delete).

        Args:
            bot_id: ID of the bot to delete

        Returns:
            bool: True if deleted successfully
        """
        try:
            telegram_bot = await self.db_session.get(TelegramBot, bot_id)
            if not telegram_bot:
                return False

            # Stop bot if running
            logger.info(f"Stopping bot {bot_id} before deletion")
            await self.deployment_service.deactivate_telegram_bot(bot_id)

            import asyncio

            await asyncio.sleep(1)

            # Soft delete
            telegram_bot.deleted_at = datetime.now(UTC)
            telegram_bot.is_active = False
            telegram_bot.connection_status = "disconnected"

            await self.db_session.commit()

            logger.info(f"Deleted Telegram bot {bot_id}")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to delete Telegram bot {bot_id}: {str(e)}")
            return False

    async def get_bot(self, bot_id: UUID) -> TelegramBot | None:
        """Get a Telegram bot by ID."""
        return await self.db_session.get(TelegramBot, bot_id)

    async def list_bots(
        self, tenant_id: UUID | None = None, agent_id: UUID | None = None, is_active: bool | None = None
    ) -> list[TelegramBot]:
        """
        List Telegram bots with optional filters.

        Args:
            tenant_id: Filter by tenant ID (optional)
            agent_id: Filter by agent ID (optional)
            is_active: Filter by active status (optional)

        Returns:
            List[TelegramBot]: List of bots
        """
        stmt = select(TelegramBot).where(TelegramBot.deleted_at.is_(None))

        if tenant_id:
            stmt = stmt.where(TelegramBot.tenant_id == tenant_id)

        if agent_id:
            stmt = stmt.where(TelegramBot.agent_id == agent_id)

        if is_active is not None:
            stmt = stmt.where(TelegramBot.is_active == is_active)

        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())

    async def start_bot(self, bot_id: UUID, webhook_base_url: str | None = None) -> bool:
        """
        Start a Telegram bot.

        For polling mode: Activates via worker pool.
        For webhook mode: Registers webhook URL with Telegram.

        Args:
            bot_id: ID of the bot to start
            webhook_base_url: Base URL for webhook (e.g., https://api.example.com).
                              Required for webhook mode if not set in constructor.

        Returns:
            bool: True if started successfully
        """
        try:
            telegram_bot = await self.db_session.get(TelegramBot, bot_id)
            if not telegram_bot:
                raise ValueError(f"Telegram bot {bot_id} not found")

            # Check if using webhook mode
            if telegram_bot.use_webhook:
                base_url = webhook_base_url or self.webhook_base_url
                if not base_url:
                    raise ValueError("webhook_base_url is required for webhook mode")

                success = await self.webhook_service.setup_webhook(telegram_bot, base_url)
                if success:
                    logger.info(f"Set up webhook for Telegram bot {bot_id}")
                else:
                    logger.error(f"Failed to set up webhook for Telegram bot {bot_id}")
                return success
            else:
                # Use polling mode via worker pool
                result = await self.deployment_service.activate_telegram_bot(bot_id)
                if result.get("success"):
                    logger.info(
                        f"Activation request sent for Telegram bot {bot_id}, assigned to worker {result.get('assigned_worker')}"
                    )
                    return True
                else:
                    logger.error(f"Failed to activate Telegram bot {bot_id}: {result.get('error')}")
                    return False

        except Exception as e:
            logger.error(f"Error starting Telegram bot {bot_id}: {str(e)}")
            return False

    async def stop_bot(self, bot_id: UUID) -> bool:
        """
        Stop a running Telegram bot.

        For polling mode: Deactivates via worker pool.
        For webhook mode: Removes the webhook from Telegram.

        Args:
            bot_id: ID of the bot to stop

        Returns:
            bool: True if stopped successfully
        """
        telegram_bot = await self.db_session.get(TelegramBot, bot_id)

        if telegram_bot and telegram_bot.use_webhook:
            return await self.webhook_service.remove_webhook(telegram_bot)
        else:
            try:
                result = await self.deployment_service.deactivate_telegram_bot(bot_id)
                return result.get("success", False)
            except Exception as e:
                logger.error(f"Error stopping Telegram bot {bot_id}: {str(e)}")
                return False

    async def restart_bot(self, bot_id: UUID) -> bool:
        """
        Restart a Telegram bot.

        Args:
            bot_id: ID of the bot to restart

        Returns:
            bool: True if restarted successfully
        """
        try:
            telegram_bot = await self.db_session.get(TelegramBot, bot_id)

            if telegram_bot and telegram_bot.use_webhook:
                # For webhook mode, use the old flow
                await self.stop_bot(bot_id)
                import asyncio

                await asyncio.sleep(1)
                return await self.start_bot(bot_id)
            else:
                # For polling mode, use worker pool
                from ...bot_worker.redis_state import BotType

                result = self.deployment_service.restart_bot(str(bot_id), BotType.TELEGRAM)
                return result.get("success", False)

        except Exception as e:
            logger.error(f"Error restarting Telegram bot {bot_id}: {str(e)}")
            return False

    async def get_bot_status(self, bot_id: UUID) -> dict[str, Any]:
        """
        Get detailed status of a Telegram bot.

        Args:
            bot_id: ID of the bot

        Returns:
            Dict: Bot status information
        """
        telegram_bot = await self.db_session.get(TelegramBot, bot_id)
        if not telegram_bot:
            return {"error": "Bot not found"}

        # Get deployment status from worker pool
        deployment_status = self.deployment_service.get_bot_status(str(bot_id))

        # Get agent info
        agent = await self.db_session.get(Agent, telegram_bot.agent_id)

        return {
            "bot_id": str(telegram_bot.id),
            "bot_name": telegram_bot.bot_name,
            "bot_username": telegram_bot.bot_username,
            "telegram_bot_id": telegram_bot.telegram_bot_id,
            "agent_id": str(telegram_bot.agent_id),
            "agent_name": agent.agent_name if agent else None,
            "use_webhook": telegram_bot.use_webhook,
            "is_active": telegram_bot.is_active,
            "connection_status": telegram_bot.connection_status,
            "is_running": deployment_status.get("is_deployed", False),
            "assigned_worker": deployment_status.get("assigned_worker"),
            "worker_healthy": deployment_status.get("worker_healthy"),
            "last_connected_at": telegram_bot.last_connected_at.isoformat() if telegram_bot.last_connected_at else None,
            "last_error": telegram_bot.last_error,
            "created_at": telegram_bot.created_at.isoformat(),
            "updated_at": telegram_bot.updated_at.isoformat(),
        }

    async def start_all_active_bots(self, tenant_id: UUID | None = None) -> dict[str, int]:
        """
        Start all active bots, optionally filtered by tenant.

        Args:
            tenant_id: Filter by tenant ID (optional)

        Returns:
            Dict: Statistics about started bots
        """
        bots = await self.list_bots(tenant_id=tenant_id, is_active=True)

        started = 0
        failed = 0

        for bot in bots:
            if bot.connection_status != "connected":
                success = await self.start_bot(bot.id)
                if success:
                    started += 1
                else:
                    failed += 1

        logger.info(f"Started {started} Telegram bots, {failed} failed")

        return {
            "total": len(bots),
            "started": started,
            "failed": failed,
            "already_running": len(bots) - started - failed,
        }

    async def validate_token(self, token: str) -> dict[str, Any]:
        """
        Validate a Telegram bot token.

        Args:
            token: Bot token to validate

        Returns:
            Dict with validation result
        """
        return await TelegramAuth.test_token(token)
