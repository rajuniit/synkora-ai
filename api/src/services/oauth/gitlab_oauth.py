"""
GitLab OAuth Implementation.

Provides OAuth authentication for GitLab API access with self-hosted instance support.
"""

import logging
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class GitLabOAuth:
    """GitLab OAuth 2.0 authentication handler with self-hosted support."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, base_url: str = "https://gitlab.com"):
        """
        Initialize GitLab OAuth handler.

        Args:
            client_id: GitLab OAuth app client ID
            client_secret: GitLab OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
            base_url: GitLab instance URL (default: https://gitlab.com)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # Support configurable base_url for self-hosted instances
        self.base_url = base_url.rstrip("/")
        self._AUTH_URL = f"{self.base_url}/oauth/authorize"
        self._TOKEN_URL = f"{self.base_url}/oauth/token"
        self._USER_INFO_URL = f"{self.base_url}/api/v4/user"
        self._REVOKE_URL = f"{self.base_url}/oauth/revoke"

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the GitLab OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["api", "read_user", "read_repository", "write_repository"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
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
            Dict with access_token, refresh_token, expires_in, token_type

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Accept": "application/json"}

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data, headers=headers)
        response_json = response.json()

        access_token = response_json.get("access_token")

        if not access_token:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        return {
            "access_token": access_token,
            "refresh_token": response_json.get("refresh_token"),
            "expires_in": response_json.get("expires_in"),
            "token_type": response_json.get("token_type", "Bearer"),
            "created_at": response_json.get("created_at"),
        }

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: GitLab access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await get_httpx_client()
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        return user_info

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        GitLab OAuth tokens expire (typically after 2 hours), so refreshing is important.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            Dict with new access_token, refresh_token, expires_in

        Raises:
            ValueError: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Accept": "application/json"}

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data, headers=headers)
        response_json = response.json()

        access_token = response_json.get("access_token")

        if not access_token:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to refresh token: {error}")

        return {
            "access_token": access_token,
            "refresh_token": response_json.get("refresh_token"),
            "expires_in": response_json.get("expires_in"),
            "token_type": response_json.get("token_type", "Bearer"),
            "created_at": response_json.get("created_at"),
        }

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Args:
            token: Access token to revoke

        Returns:
            True if successful
        """
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "token": token,
            }

            client = await get_httpx_client()
            response = await client.post(self._REVOKE_URL, data=data)
            # GitLab returns 200 on successful revocation
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    def calculate_token_expiry(self, expires_in: int | None) -> datetime | None:
        """
        Calculate token expiration datetime.

        Args:
            expires_in: Seconds until token expires

        Returns:
            Datetime when token expires, or None if not available
        """
        if expires_in:
            return datetime.now(UTC) + timedelta(seconds=expires_in)
        return None
