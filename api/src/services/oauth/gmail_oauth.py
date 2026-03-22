"""Gmail OAuth Implementation."""

import logging
import os
import urllib.parse
from typing import Any

from google.oauth2.credentials import Credentials

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class GmailOAuth:
    """Gmail OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
    _REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    # Gmail API scopes
    # gmail.modify allows read, send, delete, and manage labels (but not permanent delete or settings)
    # gmail.readonly is kept for backward compatibility with existing connections
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(self, client_id: str | None = None, client_secret: str | None = None, redirect_uri: str | None = None):
        """
        Initialize Gmail OAuth handler.

        Args:
            client_id: Google OAuth app client ID
            client_secret: Google OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id or os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GMAIL_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("GMAIL_REDIRECT_URI", "http://localhost:3005/oauth/gmail/callback")

        if not self.client_id or not self.client_secret:
            logger.warning("Gmail OAuth credentials not configured")

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the Gmail OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request (default: Gmail read scopes)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = self.SCOPES

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
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
                - access_token: Access token
                - refresh_token: Refresh token (if available)
                - expires_in: Token expiry time in seconds
                - token_type: Token type (usually "Bearer")

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data)

        if response.status_code != 200:
            error_data = response.json()
            error = error_data.get("error_description", error_data.get("error", "Unknown error"))
            raise ValueError(f"Failed to exchange code: {error}")

        return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            New token data dictionary

        Raises:
            ValueError: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data)

        if response.status_code != 200:
            error_data = response.json()
            error = error_data.get("error_description", error_data.get("error", "Unknown error"))
            raise ValueError(f"Failed to refresh token: {error}")

        return response.json()

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: Gmail access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await get_httpx_client()
        response = await client.get(self._USER_INFO_URL, headers=headers)

        if response.status_code != 200:
            raise ValueError(f"Failed to get user info: {response.text}")

        return response.json()

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
            response = await client.post(self._REVOKE_URL, data={"token": token})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    def create_credentials(self, access_token: str, refresh_token: str | None = None) -> Credentials:
        """
        Create Google credentials object.

        Args:
            access_token: Access token
            refresh_token: Optional refresh token

        Returns:
            Google Credentials object
        """
        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=self._TOKEN_URL,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )

    async def test_token(self, token: str) -> dict[str, Any]:
        """
        Test if a token is valid.

        Args:
            token: Access token to test

        Returns:
            Test result dictionary
        """
        try:
            user_info = await self.get_user_info(token)
            return {"valid": True, "email": user_info.get("email"), "name": user_info.get("name")}
        except Exception as e:
            logger.error(f"Token test failed: {e}")
            return {"valid": False, "error": str(e)}
