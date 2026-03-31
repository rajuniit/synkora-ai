"""
LinkedIn OAuth 2.0 Implementation.

Provides OAuth 2.0 authentication for LinkedIn API access.
Uses the Authorization Code Flow for server-side applications.

LinkedIn requires OAuth 2.0 for accessing user data and posting content.
"""

import logging
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class LinkedInOAuth:
    """LinkedIn OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    _TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    _USER_INFO_URL = "https://api.linkedin.com/v2/userinfo"
    _REVOKE_URL = "https://www.linkedin.com/oauth/v2/revoke"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize LinkedIn OAuth handler.

        Args:
            client_id: LinkedIn OAuth app client ID
            client_secret: LinkedIn OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(
        self,
        state: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        """
        Get the LinkedIn OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: OAuth scopes to request

        Returns:
            Authorization URL
        """
        if scopes is None:
            # Default scopes for basic profile and posting
            scopes = ["openid", "profile", "email", "w_member_social", "w_organization_social", "r_organization_social"]

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
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
            Dictionary containing access_token, expires_in, refresh_token (if available)

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client = await get_httpx_client()
        response = await client.post(
            self._TOKEN_URL,
            data=data,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("error_description", error_data.get("error", "Unknown error"))
            logger.error(f"LinkedIn token exchange failed: {error}")
            raise ValueError(f"Failed to get access token: {error}")

        token_data = response.json()

        return {
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token"),
            "refresh_token_expires_in": token_data.get("refresh_token_expires_in"),
            "scope": token_data.get("scope"),
            "token_type": token_data.get("token_type", "Bearer"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            Dictionary containing new access_token, expires_in

        Raises:
            ValueError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client = await get_httpx_client()
        response = await client.post(
            self._TOKEN_URL,
            data=data,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("error_description", error_data.get("error", "Unknown error"))
            logger.error(f"LinkedIn token refresh failed: {error}")
            raise ValueError(f"Failed to refresh token: {error}")

        token_data = response.json()

        return {
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token"),
            "refresh_token_expires_in": token_data.get("refresh_token_expires_in"),
            "scope": token_data.get("scope"),
            "token_type": token_data.get("token_type", "Bearer"),
        }

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Uses the OpenID Connect userinfo endpoint for basic profile data.

        Args:
            access_token: LinkedIn access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        client = await get_httpx_client()
        response = await client.get(
            self._USER_INFO_URL,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("message", error_data.get("error", "Unknown error"))
            logger.error(f"LinkedIn get user info failed: {error}")
            raise ValueError(f"Failed to get user info: {error}")

        data = response.json()

        return {
            "id": data.get("sub"),
            "name": data.get("name"),
            "given_name": data.get("given_name"),
            "family_name": data.get("family_name"),
            "picture": data.get("picture"),
            "email": data.get("email"),
            "email_verified": data.get("email_verified"),
            "locale": data.get("locale"),
        }

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Args:
            token: Access token to revoke

        Returns:
            True if revocation was successful
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token": token,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        client = await get_httpx_client()
        response = await client.post(
            self._REVOKE_URL,
            data=data,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code == 200:
            logger.info("LinkedIn token revoked successfully")
            return True
        else:
            logger.warning(f"LinkedIn token revocation returned status {response.status_code}")
            return False
