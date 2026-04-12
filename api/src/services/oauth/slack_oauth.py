"""Slack OAuth Implementation."""

import logging
import os
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class SlackOAuth:
    """Slack OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://slack.com/oauth/v2/authorize"
    _TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    _USER_INFO_URL = "https://slack.com/api/users.identity"

    def __init__(self, client_id: str | None = None, client_secret: str | None = None, redirect_uri: str | None = None):
        """
        Initialize Slack OAuth handler.

        Args:
            client_id: Slack OAuth app client ID
            client_secret: Slack OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id or os.getenv("SLACK_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("SLACK_REDIRECT_URI", "https://synkora.ai/oauth/slack/callback")

        if not self.client_id or not self.client_secret:
            logger.warning("Slack OAuth credentials not configured")

    def get_authorization_url(
        self, state: str | None = None, scopes: list[str] | None = None, user_scopes: list[str] | None = None
    ) -> str:
        """
        Get the Slack OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of bot OAuth scopes to request
            user_scopes: List of user OAuth scopes to request

        Returns:
            Authorization URL
        """
        if scopes is None:
            # Default bot scopes for reading messages
            scopes = [
                "channels:history",
                "channels:read",
                "groups:history",
                "groups:read",
                "im:history",
                "im:read",
                "mpim:history",
                "mpim:read",
                "users:read",
                "team:read",
            ]

        if user_scopes is None:
            user_scopes = ["identity.basic", "identity.email"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(scopes),
            "user_scope": ",".join(user_scopes),
        }

        if state:
            params["state"] = state

        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token data dictionary containing:
                - access_token: Bot access token
                - team: Team information
                - authed_user: Authenticated user information
                - bot_user_id: Bot user ID

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data)
        response_json = response.json()

        if not response_json.get("ok"):
            error = response_json.get("error", "Unknown error")
            raise ValueError(f"Failed to exchange code: {error}")

        return {
            "access_token": response_json.get("access_token"),
            "team": response_json.get("team"),
            "authed_user": response_json.get("authed_user"),
            "bot_user_id": response_json.get("bot_user_id"),
            "scope": response_json.get("scope"),
            "token_type": response_json.get("token_type"),
        }

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: Slack access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await get_httpx_client()
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response_json = response.json()

        if not response_json.get("ok"):
            error = response_json.get("error", "Unknown error")
            raise ValueError(f"Failed to get user info: {error}")

        return response_json.get("user", {})

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Args:
            token: Access token to revoke

        Returns:
            True if successful
        """
        try:
            client = await get_httpx_client()
            response = await client.post(
                "https://slack.com/api/auth.revoke", headers={"Authorization": f"Bearer {token}"}
            )
            response_json = response.json()
            return response_json.get("ok", False)
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def test_token(self, token: str) -> dict[str, Any]:
        """
        Test if a token is valid.

        Args:
            token: Access token to test

        Returns:
            Test result dictionary
        """
        try:
            client = await get_httpx_client()
            response = await client.post(
                "https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to test token: {e}")
            return {"ok": False, "error": str(e)}
