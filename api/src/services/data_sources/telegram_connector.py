"""Telegram data source connector."""

import json
import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource
from src.models.document import Document
from src.services.storage.s3_storage import S3StorageService

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramConnector(BaseConnector):
    """
    Connector for Telegram bot data.

    Note: Telegram's API is more limited than Slack:
    - Bots can only access messages sent directly to them or in groups where they're mentioned
    - Historical message access is limited (getUpdates only returns recent updates)
    - This connector is primarily for syncing messages the bot receives
    """

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """
        Initialize Telegram connector.

        Args:
            data_source: DataSource model instance
            db: Async database session
        """
        super().__init__(data_source, db)
        self.bot_token: str | None = None
        self.bot_info: dict | None = None

    async def connect(self) -> bool:
        """Establish connection to Telegram by validating the bot token."""
        try:
            # Get bot token from config
            config = self.data_source.config or {}
            bot_token = config.get("bot_token")

            if not bot_token:
                # Try encrypted field
                if self.data_source.access_token_encrypted:
                    from src.services.agents.security import decrypt_value

                    bot_token = decrypt_value(self.data_source.access_token_encrypted)

            if not bot_token:
                logger.error("No bot token found for Telegram data source")
                return False

            # Validate the token
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{TELEGRAM_API_BASE}/bot{bot_token}/getMe", timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        self.bot_token = bot_token
                        self.bot_info = data.get("result", {})
                        logger.info(f"Connected to Telegram bot: @{self.bot_info.get('username')}")
                        return True

                logger.error(f"Failed to connect to Telegram: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Unexpected error connecting to Telegram: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection to Telegram."""
        self.bot_token = None
        self.bot_info = None
        logger.info("Disconnected from Telegram")

    async def test_connection(self) -> dict[str, Any]:
        """Test the Telegram connection."""
        try:
            if not self.bot_token:
                connected = await self.connect()
                if not connected:
                    return {
                        "success": False,
                        "message": "Failed to connect to Telegram. Please check your bot token.",
                        "details": {},
                    }

            return {
                "success": True,
                "message": f"Successfully connected to Telegram bot @{self.bot_info.get('username')}",
                "details": {
                    "bot_id": self.bot_info.get("id"),
                    "username": self.bot_info.get("username"),
                    "first_name": self.bot_info.get("first_name"),
                    "can_join_groups": self.bot_info.get("can_join_groups", False),
                    "can_read_all_group_messages": self.bot_info.get("can_read_all_group_messages", False),
                },
            }

        except Exception as e:
            return {"success": False, "message": f"Unexpected error: {str(e)}", "details": {"error": str(e)}}

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Fetch recent messages from Telegram using getUpdates.

        Note: This only returns recent updates (messages sent to the bot).
        Telegram doesn't allow bots to access historical chat messages.

        Args:
            since: Not fully supported - Telegram only provides recent updates
            limit: Maximum number of updates to fetch
        """
        if not self.bot_token:
            raise ConnectionError("Not connected to Telegram")

        documents = []
        config = self.data_source.config or {}

        # Get the last update offset (to avoid duplicates)
        last_update_id = config.get("last_update_id", 0)

        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "offset": last_update_id + 1 if last_update_id else None,
                    "limit": min(limit or 100, 100),  # Telegram max is 100
                    "timeout": 0,  # Short polling for sync
                }
                # Remove None values
                params = {k: v for k, v in params.items() if v is not None}

                response = await client.get(
                    f"{TELEGRAM_API_BASE}/bot{self.bot_token}/getUpdates", params=params, timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        updates = data.get("result", [])

                        for update in updates:
                            doc = self._process_update(update)
                            if doc:
                                documents.append(doc)
                                # Track last update ID
                                if update.get("update_id", 0) > last_update_id:
                                    last_update_id = update["update_id"]

                        # Update config with last update ID
                        if last_update_id:
                            self.data_source.config = {**config, "last_update_id": last_update_id}
                            await self.db.commit()

        except Exception as e:
            logger.error(f"Error fetching Telegram updates: {e}")

        return documents[:limit] if limit else documents

    def _process_update(self, update: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a Telegram update into a document.

        Args:
            update: Telegram update object

        Returns:
            Document dict or None if not a message
        """
        message = update.get("message") or update.get("channel_post")
        if not message:
            return None

        # Extract message info
        chat = message.get("chat", {})
        from_user = message.get("from", {})
        text = message.get("text", "")

        # Skip if no text content
        if not text:
            return None

        # Build document
        message_id = message.get("message_id", 0)
        chat_id = chat.get("id", 0)
        timestamp = datetime.fromtimestamp(message.get("date", 0))

        # Determine chat type and title
        chat_type = chat.get("type", "private")
        chat_title = chat.get("title") or chat.get("username") or f"Chat {chat_id}"

        # Get user info
        user_name = from_user.get("username", "")
        user_display = f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()

        return {
            "id": f"tg_{chat_id}_{message_id}",
            "text": text,
            "metadata": {
                "source": "TELEGRAM",
                "chat_id": chat_id,
                "chat_type": chat_type,
                "chat_title": chat_title,
                "message_id": message_id,
                "user_id": from_user.get("id"),
                "user_name": user_name,
                "user_display": user_display or user_name,
                "timestamp": timestamp.isoformat(),
                "update_id": update.get("update_id"),
                "is_bot": from_user.get("is_bot", False),
            },
        }

    async def _store_message_to_s3_and_db(
        self, message_data: dict[str, Any], raw_message: dict[str, Any]
    ) -> Document | None:
        """
        Store message to S3 and create Document record.
        """
        try:
            s3 = S3StorageService()

            timestamp = datetime.fromisoformat(message_data["metadata"]["timestamp"])
            filename = f"message-{message_data['id']}.json"
            s3_key = s3.generate_key(
                tenant_id=self.data_source.tenant_id, source_type="TELEGRAM", filename=filename, timestamp=timestamp
            )

            raw_json = json.dumps(raw_message, indent=2)
            s3_result = s3.upload_file(
                file_content=raw_json.encode("utf-8"),
                key=s3_key,
                content_type="application/json",
                metadata={
                    "chat_id": str(message_data["metadata"]["chat_id"]),
                    "user": message_data["metadata"]["user_display"],
                    "timestamp": message_data["metadata"]["timestamp"],
                },
            )

            # Telegram message URL (only works for public channels)
            message_data["metadata"]["chat_id"]
            message_id = message_data["metadata"]["message_id"]
            telegram_url = None
            if message_data["metadata"]["chat_type"] == "channel":
                # For public channels, URL might be accessible
                chat_username = message_data["metadata"].get("chat_username")
                if chat_username:
                    telegram_url = f"https://t.me/{chat_username}/{message_id}"

            document = Document(
                tenant_id=self.data_source.tenant_id,
                knowledge_base_id=None,
                data_source_id=self.data_source.id,
                title=f"Telegram message in {message_data['metadata']['chat_title']}",
                content=message_data["text"],
                source_type="TELEGRAM",
                external_id=message_data["id"],
                external_url=telegram_url,
                s3_bucket=s3_result["bucket"],
                s3_key=s3_result["key"],
                s3_url=s3_result["url"],
                file_size=len(raw_json),
                mime_type="application/json",
                metadata={
                    "chat_id": message_data["metadata"]["chat_id"],
                    "chat_type": message_data["metadata"]["chat_type"],
                    "chat_title": message_data["metadata"]["chat_title"],
                    "user_id": message_data["metadata"]["user_id"],
                    "user_name": message_data["metadata"]["user_name"],
                    "user_display": message_data["metadata"]["user_display"],
                    "message_id": message_data["metadata"]["message_id"],
                    "timestamp": message_data["metadata"]["timestamp"],
                },
            )

            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            logger.info(f"Stored Telegram message {message_data['id']} to S3 and DB")
            return document

        except Exception as e:
            logger.error(f"Failed to store message to S3/DB: {e}")
            await self.db.rollback()
            return None

    async def sync_to_knowledge_base(
        self, knowledge_base_id: str, since: datetime | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        """
        Sync Telegram messages to knowledge base.
        """
        try:
            if not self.bot_token:
                await self.connect()

            messages = await self.fetch_documents(since=since, limit=limit)

            stored_count = 0
            failed_count = 0

            for msg_data in messages:
                raw_message = {
                    "message_id": msg_data["metadata"]["message_id"],
                    "chat": {
                        "id": msg_data["metadata"]["chat_id"],
                        "type": msg_data["metadata"]["chat_type"],
                        "title": msg_data["metadata"]["chat_title"],
                    },
                    "from": {
                        "id": msg_data["metadata"]["user_id"],
                        "username": msg_data["metadata"]["user_name"],
                    },
                    "text": msg_data["text"],
                    "date": int(datetime.fromisoformat(msg_data["metadata"]["timestamp"]).timestamp()),
                }

                document = await self._store_message_to_s3_and_db(msg_data, raw_message)

                if document:
                    document.knowledge_base_id = knowledge_base_id
                    await self.db.commit()
                    stored_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_fetched": len(messages),
                "stored": stored_count,
                "failed": failed_count,
                "message": f"Synced {stored_count} messages to knowledge base",
            }

        except Exception as e:
            logger.error(f"Sync to knowledge base failed: {e}")
            return {"success": False, "error": str(e), "message": "Failed to sync messages"}

    async def get_document_count(self) -> int:
        """Get count of documents from the last fetch."""
        return len(await self.fetch_documents())

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return ["bot_token"]

    def get_oauth_url(self) -> str | None:
        """
        Telegram doesn't use OAuth - it uses bot tokens from BotFather.
        Return None to indicate manual token entry is required.
        """
        return None

    async def handle_oauth_callback(self, code: str) -> dict[str, Any]:
        """
        Telegram doesn't use OAuth.
        This method validates a bot token directly.
        """
        try:
            from src.services.oauth.telegram_auth import TelegramAuth

            # The 'code' in this case is actually the bot token
            result = await TelegramAuth.validate_token(code)

            if result["success"]:
                # Store the token (encrypted)
                from src.services.agents.security import encrypt_value

                self.data_source.access_token_encrypted = encrypt_value(code)
                self.data_source.config = {
                    **self.data_source.config,
                    "bot_id": result.get("bot_id"),
                    "bot_username": result.get("bot_username"),
                }
                await self.db.commit()

                return {
                    "success": True,
                    "message": f"Successfully connected to Telegram bot @{result.get('bot_username')}",
                    "bot_username": result.get("bot_username"),
                }
            else:
                return {"success": False, "message": result.get("error", "Token validation failed")}

        except Exception as e:
            logger.warning(f"Token validation error: {e}")
            return {"success": False, "message": f"Failed to validate token: {str(e)}"}
