"""
Micromobility OAuth Implementation.

Generic OAuth 2.0 service for micromobility platforms (scooters, bikes, fleet management).
Unlike provider-specific implementations, all URLs are configurable via constructor args
sourced from OAuthApp.config — enabling any micromobility API to be connected.
"""

import logging
import urllib.parse
from typing import Any

from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class MicromobilityOAuth:
    """Generic OAuth 2.0 handler for micromobility platforms."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorize_url: str,
        token_url: str,
        base_url: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.base_url = base_url.rstrip("/")

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """Build the provider-specific authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }

        if scopes:
            params["scope"] = " ".join(scopes)

        if state:
            params["state"] = state

        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}"

    async def get_access_token(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        client = await get_httpx_client()
        response = await client.post(self.token_url, json=data, headers={"Content-Type": "application/json"})
        response_json = response.json()

        if response.status_code != 200:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        return response_json

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """Fetch user/account info from the provider. Falls back to a stub if the endpoint fails."""
        try:
            client = await get_httpx_client()
            response = await client.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Micromobility /me endpoint failed (provider may not support it): {e}")

        # Return a minimal stub so the OAuth flow can still complete
        return {"authenticated": True}

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        client = await get_httpx_client()
        response = await client.post(self.token_url, json=data, headers={"Content-Type": "application/json"})
        response_json = response.json()

        if response.status_code != 200:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to refresh token: {error}")

        return response_json

    async def revoke_token(self, token: str) -> bool:
        """Best-effort token revocation — provider-specific, may not be supported."""
        try:
            revoke_url = f"{self.base_url}/oauth/revoke"
            client = await get_httpx_client()
            response = await client.post(
                revoke_url,
                json={"token": token},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            return response.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Micromobility token revocation failed (may not be supported): {e}")
            return False
