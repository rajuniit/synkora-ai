"""
Google OAuth Implementation.

Provides OAuth authentication for Google services (Sign in with Google).
"""

import logging
import os
import urllib.parse
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.social_auth.provider_config_service import SocialAuthProviderConfigService
from .base_oauth import BaseOAuthService
from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class GoogleOAuth(BaseOAuthService):
    """Google OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    _REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    @classmethod
    async def from_database(cls, db: AsyncSession, tenant_id: str) -> "GoogleOAuth":
        """
        Create GoogleOAuth instance from database configuration.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            GoogleOAuth instance

        Raises:
            ValueError: If configuration not found or incomplete
        """
        from uuid import UUID

        # Convert tenant_id to UUID if it's a string
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        config = await SocialAuthProviderConfigService.get_provider(db, tenant_id, "google", decrypt_secret=True)

        if not config:
            raise ValueError("Google OAuth is not configured")

        if config.get("enabled") != "true":
            raise ValueError("Google OAuth is not enabled")

        if not config.get("client_id") or not config.get("client_secret"):
            raise ValueError("Google OAuth configuration is incomplete")

        redirect_uri = config.get("redirect_uri") or os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")

        return cls(client_id=config["client_id"], client_secret=config["client_secret"], redirect_uri=redirect_uri)

    @classmethod
    def from_env(cls) -> "GoogleOAuth":
        """
        Create GoogleOAuth instance from environment variables.

        Returns:
            GoogleOAuth instance

        Raises:
            ValueError: If required environment variables are missing
        """
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")

        if not client_id or not client_secret:
            raise ValueError("Google OAuth environment variables not configured")

        return cls(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request (default: openid, email, profile)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["openid", "email", "profile"]

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
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data)
        response_json = response.json()

        if "error" in response_json:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        return response_json

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: Google access token

        Returns:
            User information dictionary with:
            - id: Google user ID
            - email: User email
            - name: User display name
            - picture: Profile picture URL
            - verified_email: Whether email is verified
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

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary containing new access_token and expires_in

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
        response_json = response.json()

        if "error" in response_json:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to refresh token: {error}")

        return response_json

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Args:
            token: Access token to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            params = {"token": token}
            client = await get_httpx_client()
            response = await client.post(self._REVOKE_URL, params=params)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
