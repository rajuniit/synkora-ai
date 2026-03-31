"""
Twitter/X OAuth 2.0 Implementation.

Provides OAuth 2.0 authentication for Twitter API v2 access.
Uses the Authorization Code Flow with PKCE for enhanced security.

Twitter API v2 requires OAuth 2.0 for most user-context endpoints.
"""

import base64
import hashlib
import logging
import secrets
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class TwitterOAuth:
    """Twitter OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    _TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    _USER_INFO_URL = "https://api.twitter.com/2/users/me"
    _REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Twitter OAuth handler.

        Args:
            client_id: Twitter OAuth app client ID
            client_secret: Twitter OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return secrets.token_urlsafe(32)

    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def get_authorization_url(
        self,
        state: str | None = None,
        scopes: list[str] | None = None,
        code_verifier: str | None = None,
    ) -> tuple[str, str]:
        """
        Get the Twitter OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: OAuth scopes to request
            code_verifier: PKCE code verifier (generated if not provided)

        Returns:
            Tuple of (authorization_url, code_verifier)
        """
        if scopes is None:
            scopes = [
                "tweet.read",
                "tweet.write",
                "users.read",
                "follows.read",
                "follows.write",
                "like.read",
                "like.write",
                "bookmark.read",
                "offline.access",
            ]

        if code_verifier is None:
            code_verifier = self._generate_code_verifier()

        code_challenge = self._generate_code_challenge(code_verifier)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state or secrets.token_urlsafe(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"
        return auth_url, code_verifier

    async def get_access_token(self, code: str, code_verifier: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier used in authorization

        Returns:
            Dictionary containing access_token, refresh_token, expires_in

        Raises:
            ValueError: If token exchange fails
        """
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        # Twitter requires Basic auth with client credentials for confidential clients
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_bytes}",
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
            logger.error(f"Twitter token exchange failed: {error}")
            raise ValueError(f"Failed to get access token: {error}")

        token_data = response.json()

        return {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            Dictionary containing new access_token, refresh_token, expires_in

        Raises:
            ValueError: If token refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_bytes}",
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
            logger.error(f"Twitter token refresh failed: {error}")
            raise ValueError(f"Failed to refresh token: {error}")

        token_data = response.json()

        return {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
        }

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            access_token: Twitter access token

        Returns:
            User information dictionary
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        params = {"user.fields": "id,name,username,description,profile_image_url,public_metrics,created_at,verified"}

        client = await get_httpx_client()
        response = await client.get(
            self._USER_INFO_URL,
            headers=headers,
            params=params,
            timeout=30.0,
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            error = error_data.get("detail", error_data.get("title", "Unknown error"))
            logger.error(f"Twitter get user info failed: {error}")
            raise ValueError(f"Failed to get user info: {error}")

        data = response.json()
        return data.get("data", {})

    async def revoke_token(self, token: str, token_type: str = "access_token") -> bool:
        """
        Revoke an access or refresh token.

        Args:
            token: Token to revoke
            token_type: Type of token ("access_token" or "refresh_token")

        Returns:
            True if revocation was successful
        """
        data = {
            "token": token,
            "token_type_hint": token_type,
            "client_id": self.client_id,
        }

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_bytes}",
        }

        client = await get_httpx_client()
        response = await client.post(
            self._REVOKE_URL,
            data=data,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code == 200:
            logger.info("Twitter token revoked successfully")
            return True
        else:
            logger.warning(f"Twitter token revocation returned status {response.status_code}")
            return False
