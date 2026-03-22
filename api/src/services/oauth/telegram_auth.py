"""Telegram Bot Token validation service."""

import logging
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramAuth:
    """Service for validating Telegram bot tokens."""

    @staticmethod
    async def validate_token(token: str) -> dict[str, Any]:
        """
        Validate a Telegram bot token by calling getMe.

        Args:
            token: Bot token from BotFather

        Returns:
            Dict with success status and bot info or error
        """
        try:
            client = await get_httpx_client()
            response = await client.get(f"{TELEGRAM_API_BASE}/bot{token}/getMe", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    return {
                        "success": True,
                        "bot_id": bot_info.get("id"),
                        "bot_username": bot_info.get("username"),
                        "bot_first_name": bot_info.get("first_name"),
                        "can_join_groups": bot_info.get("can_join_groups", False),
                        "can_read_all_group_messages": bot_info.get("can_read_all_group_messages", False),
                        "supports_inline_queries": bot_info.get("supports_inline_queries", False),
                    }
                else:
                    return {"success": False, "error": data.get("description", "Unknown error from Telegram API")}
            elif response.status_code == 401:
                return {"success": False, "error": "Invalid bot token. Please check your token from BotFather."}
            else:
                return {"success": False, "error": f"Telegram API returned status {response.status_code}"}

        except httpx.TimeoutException:
            logger.error("Timeout while validating Telegram token")
            return {"success": False, "error": "Connection timeout while validating token"}
        except Exception as e:
            logger.error(f"Error validating Telegram token: {str(e)}")
            return {"success": False, "error": f"Failed to validate token: {str(e)}"}

    @staticmethod
    async def test_token(token: str) -> dict[str, Any]:
        """
        Test a Telegram bot token and return detailed info.

        Args:
            token: Bot token from BotFather

        Returns:
            Dict with test results
        """
        result = await TelegramAuth.validate_token(token)

        if result["success"]:
            return {
                "success": True,
                "message": f"Bot @{result.get('bot_username')} is valid and ready to use",
                "details": {
                    "bot_id": result.get("bot_id"),
                    "username": result.get("bot_username"),
                    "name": result.get("bot_first_name"),
                    "can_join_groups": result.get("can_join_groups"),
                    "can_read_all_group_messages": result.get("can_read_all_group_messages"),
                    "supports_inline_queries": result.get("supports_inline_queries"),
                },
            }
        else:
            return {"success": False, "message": result.get("error", "Token validation failed"), "details": {}}

    @staticmethod
    async def set_webhook(
        token: str, url: str, secret_token: str | None = None, drop_pending_updates: bool = False
    ) -> dict[str, Any]:
        """
        Set webhook for a Telegram bot.

        Args:
            token: Bot token
            url: Webhook URL (must be HTTPS)
            secret_token: Optional secret for webhook validation
            drop_pending_updates: Whether to drop pending updates

        Returns:
            Dict with success status
        """
        try:
            params = {"url": url, "drop_pending_updates": drop_pending_updates}
            if secret_token:
                params["secret_token"] = secret_token

            client = await get_httpx_client()
            response = await client.post(f"{TELEGRAM_API_BASE}/bot{token}/setWebhook", json=params, timeout=10.0)

            data = response.json()
            if data.get("ok"):
                return {"success": True, "message": "Webhook configured successfully"}
            else:
                return {"success": False, "error": data.get("description", "Failed to set webhook")}

        except Exception as e:
            logger.error(f"Error setting Telegram webhook: {str(e)}")
            return {"success": False, "error": f"Failed to set webhook: {str(e)}"}

    @staticmethod
    async def delete_webhook(token: str, drop_pending_updates: bool = False) -> dict[str, Any]:
        """
        Delete webhook for a Telegram bot (switch to long polling).

        Args:
            token: Bot token
            drop_pending_updates: Whether to drop pending updates

        Returns:
            Dict with success status
        """
        try:
            client = await get_httpx_client()
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{token}/deleteWebhook",
                json={"drop_pending_updates": drop_pending_updates},
                timeout=10.0,
            )

            data = response.json()
            if data.get("ok"):
                return {"success": True, "message": "Webhook deleted successfully"}
            else:
                return {"success": False, "error": data.get("description", "Failed to delete webhook")}

        except Exception as e:
            logger.error(f"Error deleting Telegram webhook: {str(e)}")
            return {"success": False, "error": f"Failed to delete webhook: {str(e)}"}

    @staticmethod
    async def get_webhook_info(token: str) -> dict[str, Any]:
        """
        Get current webhook info for a bot.

        Args:
            token: Bot token

        Returns:
            Dict with webhook info
        """
        try:
            client = await get_httpx_client()
            response = await client.get(f"{TELEGRAM_API_BASE}/bot{token}/getWebhookInfo", timeout=10.0)

            data = response.json()
            if data.get("ok"):
                result = data.get("result", {})
                return {
                    "success": True,
                    "url": result.get("url", ""),
                    "has_custom_certificate": result.get("has_custom_certificate", False),
                    "pending_update_count": result.get("pending_update_count", 0),
                    "last_error_date": result.get("last_error_date"),
                    "last_error_message": result.get("last_error_message"),
                }
            else:
                return {"success": False, "error": data.get("description", "Failed to get webhook info")}

        except Exception as e:
            logger.error(f"Error getting Telegram webhook info: {str(e)}")
            return {"success": False, "error": f"Failed to get webhook info: {str(e)}"}
