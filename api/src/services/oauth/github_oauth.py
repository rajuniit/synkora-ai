"""
GitHub OAuth Implementation.

Provides OAuth authentication for GitHub API access.
"""

import logging
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class GitHubOAuth:
    """GitHub OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _USER_INFO_URL = "https://api.github.com/user"
    _EMAIL_INFO_URL = "https://api.github.com/user/emails"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize GitHub OAuth handler.

        Args:
            client_id: GitHub OAuth app client ID
            client_secret: GitHub OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the GitHub OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request (default: repo, user)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["repo", "user", "read:org"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
        }

        if state:
            params["state"] = state

        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> str:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Access token

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
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

        return access_token

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: GitHub access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"token {token}"}

        client = await get_httpx_client()
        # Get user info
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        # Get email info
        try:
            email_response = await client.get(self._EMAIL_INFO_URL, headers=headers)
            if email_response.status_code == 200:
                email_info = email_response.json()
                if isinstance(email_info, list):
                    primary_email = next((email for email in email_info if email.get("primary")), {})
                    user_info["email"] = primary_email.get("email", user_info.get("email", ""))
                else:
                    # If email_info is not a list, use the email from user_info
                    user_info["email"] = user_info.get("email", "")
            else:
                # If we don't have permission to read emails, use the email from user_info
                user_info["email"] = user_info.get("email", "")
        except Exception as e:
            logger.warning(f"Failed to get email info: {e}")
            user_info["email"] = user_info.get("email", "")

        return user_info

    async def refresh_token(self, refresh_token: str) -> str:
        """
        Refresh an expired access token.

        Note: GitHub OAuth tokens don't expire, so this is a no-op.
        Included for API compatibility.

        Args:
            refresh_token: Refresh token (not used for GitHub)

        Returns:
            Same token (GitHub tokens don't expire)
        """
        return refresh_token

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
            response = await client.delete(
                f"https://api.github.com/applications/{self.client_id}/token",
                auth=(self.client_id, self.client_secret),
                json={"access_token": token},
            )
            return response.status_code == 204
        except Exception as e:
            logger.warning(f"Failed to revoke token: {e}")
            return False
