"""
Jira OAuth Implementation.

Provides OAuth 2.0 (3LO) authentication for Atlassian Jira Cloud API access.
"""

import logging
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class JiraOAuth:
    """Jira OAuth 2.0 (3LO) authentication handler for Atlassian Cloud."""

    _AUTH_URL = "https://auth.atlassian.com/authorize"
    _TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    _ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
    _USER_INFO_URL = "https://api.atlassian.com/me"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Jira OAuth handler.

        Args:
            client_id: Jira OAuth app client ID
            client_secret: Jira OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the Jira OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["read:me", "read:jira-work", "read:jira-user", "write:jira-work", "offline_access"]

        params = {
            "audience": "api.atlassian.com",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "response_type": "code",
            "prompt": "consent",
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
            Dictionary containing access_token, refresh_token, expires_in, etc.

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Content-Type": "application/json"}

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, json=data, headers=headers)
        response_json = response.json()

        if response.status_code != 200:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        return response_json

    async def get_accessible_resources(self, token: str) -> list[dict[str, Any]]:
        """
        Get list of accessible Jira Cloud sites for this token.

        Args:
            token: Jira access token

        Returns:
            List of accessible resources with id, url, name, scopes
        """
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        client = await get_httpx_client()
        response = await client.get(self._ACCESSIBLE_RESOURCES_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: Jira access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        client = await get_httpx_client()
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        # Also get accessible resources to store cloud_id
        resources = await self.get_accessible_resources(token)
        if resources:
            user_info["cloud_id"] = resources[0].get("id")
            user_info["cloud_url"] = resources[0].get("url")
            user_info["site_name"] = resources[0].get("name")
            user_info["accessible_resources"] = resources

        return user_info

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary containing new access_token, refresh_token, expires_in

        Raises:
            ValueError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        headers = {"Content-Type": "application/json"}

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, json=data, headers=headers)
        response_json = response.json()

        if response.status_code != 200:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to refresh token: {error}")

        return response_json

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Note: Atlassian doesn't have a token revocation endpoint.
        The token will expire naturally.

        Args:
            token: Access token to revoke

        Returns:
            True (always, as there's no revocation endpoint)
        """
        logger.info("Jira token revocation requested - tokens expire naturally")
        return True
