"""
Microsoft OAuth Implementation.

Provides OAuth authentication for Microsoft services (Sign in with Microsoft).
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


class MicrosoftOAuth(BaseOAuthService):
    """Microsoft OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    _TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    _USER_INFO_URL = "https://graph.microsoft.com/v1.0/me"

    @classmethod
    async def from_database(cls, db: AsyncSession, tenant_id: str) -> "MicrosoftOAuth":
        """
        Create MicrosoftOAuth instance from database configuration.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            MicrosoftOAuth instance

        Raises:
            ValueError: If configuration not found or incomplete
        """
        from uuid import UUID

        # Convert tenant_id to UUID if it's a string
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        config = await SocialAuthProviderConfigService.get_provider(db, tenant_id, "microsoft", decrypt_secret=True)

        if not config:
            raise ValueError("Microsoft OAuth is not configured")

        if config.get("enabled") != "true":
            raise ValueError("Microsoft OAuth is not enabled")

        if not config.get("client_id") or not config.get("client_secret"):
            raise ValueError("Microsoft OAuth configuration is incomplete")

        redirect_uri = config.get("redirect_uri") or os.getenv("MICROSOFT_OAUTH_REDIRECT_URI", "")

        return cls(client_id=config["client_id"], client_secret=config["client_secret"], redirect_uri=redirect_uri)

    @classmethod
    def from_env(cls) -> "MicrosoftOAuth":
        """
        Create MicrosoftOAuth instance from environment variables.

        Returns:
            MicrosoftOAuth instance

        Raises:
            ValueError: If required environment variables are missing
        """
        client_id = os.getenv("MICROSOFT_OAUTH_CLIENT_ID")
        client_secret = os.getenv("MICROSOFT_OAUTH_CLIENT_SECRET")
        redirect_uri = os.getenv("MICROSOFT_OAUTH_REDIRECT_URI", "")

        if not client_id or not client_secret:
            raise ValueError("Microsoft OAuth environment variables not configured")

        return cls(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the Microsoft OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request (default: openid, email, profile)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["openid", "email", "profile", "User.Read"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "response_mode": "query",
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
            token: Microsoft access token

        Returns:
            User information dictionary with:
            - id: Microsoft user ID
            - email: User email (from userPrincipalName or mail)
            - name: User display name
            - picture: Profile picture URL (if available)
        """
        headers = {"Authorization": f"Bearer {token}"}

        client = await get_httpx_client()
        response = await client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = response.json()

        # Normalize the response to match our expected format
        normalized = {
            "id": user_info.get("id"),
            "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "name": user_info.get("displayName"),
        }

        # Try to get profile picture
        try:
            photo_response = await client.get("https://graph.microsoft.com/v1.0/me/photo/$value", headers=headers)
            if photo_response.status_code == 200:
                # In a real implementation, you'd upload this to your storage
                # For now, we'll just note that a picture is available
                normalized["picture"] = "available"
        except Exception as e:
            logger.debug(f"Could not fetch profile picture: {e}")

        return normalized

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

        Note: Microsoft doesn't provide a standard revoke endpoint.
        Tokens expire naturally based on their lifetime.

        Args:
            token: Access token to revoke

        Returns:
            True (tokens expire naturally)
        """
        logger.info("Microsoft tokens expire naturally; no revocation endpoint available")
        return True
