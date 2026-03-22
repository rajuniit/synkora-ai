"""
ClickUp OAuth Implementation.

Provides OAuth 2.0 authentication for ClickUp API access.
"""

import logging
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class ClickUpOAuth:
    """ClickUp OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://app.clickup.com/api"
    _TOKEN_URL = "https://api.clickup.com/api/v2/oauth/token"
    _USER_INFO_URL = "https://api.clickup.com/api/v2/user"
    _TEAMS_URL = "https://api.clickup.com/api/v2/team"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize ClickUp OAuth handler.

        Args:
            client_id: ClickUp OAuth app client ID
            client_secret: ClickUp OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the ClickUp OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: Not used for ClickUp (ClickUp doesn't use scopes in OAuth)

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }

        if state:
            params["state"] = state

        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dictionary containing access_token

        Raises:
            ValueError: If token exchange fails
        """
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, params=params)
        response_json = response.json()

        if response.status_code != 200:
            error = response_json.get("err", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        access_token = response_json.get("access_token")
        if not access_token:
            raise ValueError("No access token in response")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
        }

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: ClickUp access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": token}

        client = await get_httpx_client()
        # Get user info
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        user_info = user_data.get("user", {})

        # Get teams/workspaces
        try:
            teams_response = await client.get(self._TEAMS_URL, headers=headers)
            if teams_response.status_code == 200:
                teams_data = teams_response.json()
                user_info["teams"] = teams_data.get("teams", [])
        except Exception as e:
            logger.warning(f"Failed to get teams info: {e}")
            user_info["teams"] = []

        return user_info

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Note: ClickUp OAuth tokens don't expire, so this is a no-op.
        Included for API compatibility.

        Args:
            refresh_token: Refresh token (not used for ClickUp)

        Returns:
            Empty dict (ClickUp tokens don't expire)
        """
        logger.info("ClickUp tokens don't expire - refresh not needed")
        return {"access_token": refresh_token}

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Note: ClickUp doesn't have a token revocation endpoint.
        Users must revoke access from their ClickUp settings.

        Args:
            token: Access token to revoke

        Returns:
            True (always, as there's no revocation endpoint)
        """
        logger.info("ClickUp token revocation requested - must be done from ClickUp settings")
        return True
