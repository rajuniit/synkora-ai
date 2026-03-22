"""
Zoom OAuth service.

Handles OAuth authentication with Zoom API.
"""

import logging
from typing import Any

import aiohttp

from .http_client import get_aiohttp_session

logger = logging.getLogger(__name__)


class ZoomOAuth:
    """Zoom OAuth client."""

    AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
    TOKEN_URL = "https://zoom.us/oauth/token"
    USER_INFO_URL = "https://api.zoom.us/v2/users/me"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Zoom OAuth client.

        Args:
            client_id: Zoom OAuth client ID
            client_secret: Zoom OAuth client secret
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """
        Get Zoom OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTHORIZE_URL}?{query_string}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Zoom

        Returns:
            Token response data
        """
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}

        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)

        session = await get_aiohttp_session()
        async with session.post(self.TOKEN_URL, data=data, auth=auth) as response:
            if response.status != 200:
                error_data = await response.text()
                logger.error(f"Zoom token exchange failed: {error_data}")
                raise Exception(f"Failed to exchange code for token: {response.status}")

            return await response.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information from Zoom.

        Args:
            access_token: Zoom access token

        Returns:
            User information
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        session = await get_aiohttp_session()
        async with session.get(self.USER_INFO_URL, headers=headers) as response:
            if response.status != 200:
                error_data = await response.text()
                logger.error(f"Zoom user info request failed: {error_data}")
                raise Exception(f"Failed to get user info: {response.status}")

            return await response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh Zoom access token.

        Args:
            refresh_token: Refresh token

        Returns:
            New token data
        """
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)

        session = await get_aiohttp_session()
        async with session.post(self.TOKEN_URL, data=data, auth=auth) as response:
            if response.status != 200:
                error_data = await response.text()
                logger.error(f"Zoom token refresh failed: {error_data}")
                raise Exception(f"Failed to refresh token: {response.status}")

            return await response.json()
