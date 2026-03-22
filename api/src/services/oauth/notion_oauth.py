"""
Notion OAuth 2.0 Provider

Handles OAuth authentication flow for Notion API access.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from src.services.oauth.base_oauth import BaseOAuthProvider
from src.services.oauth.http_client import get_httpx_client


class NotionOAuthProvider(BaseOAuthProvider):
    """OAuth provider for Notion API"""

    def __init__(self):
        super().__init__()
        self.provider_name = "notion"
        self.auth_url = "https://api.notion.com/v1/oauth/authorize"
        self.token_url = "https://api.notion.com/v1/oauth/token"
        self.scopes = []  # Notion doesn't use scopes in the traditional sense

    def get_authorization_url(self, client_id: str, redirect_uri: str, state: str, **kwargs) -> str:
        """
        Generate Notion OAuth authorization URL

        Args:
            client_id: Notion OAuth client ID
            redirect_uri: Callback URL
            state: State parameter for CSRF protection
            **kwargs: Additional parameters

        Returns:
            Authorization URL
        """
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "owner": "user",  # Can be 'user' or 'workspace'
            "state": state,
        }

        return self._build_url(self.auth_url, params)

    async def exchange_code_for_token(
        self, code: str, client_id: str, client_secret: str, redirect_uri: str, **kwargs
    ) -> dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code
            client_id: Notion OAuth client ID
            client_secret: Notion OAuth client secret
            redirect_uri: Callback URL
            **kwargs: Additional parameters

        Returns:
            Token response with access_token, workspace info, etc.
        """
        import base64

        # Notion requires Basic Auth with base64 encoded client_id:client_secret
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        client = await get_httpx_client()
        response = await client.post(self.token_url, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        token_data = response.json()

        # Notion tokens don't expire, but we'll set a far future date
        token_data["expires_at"] = (datetime.now(UTC) + timedelta(days=3650)).isoformat()

        return token_data

    async def refresh_token(self, refresh_token: str, client_id: str, client_secret: str, **kwargs) -> dict[str, Any]:
        """
        Refresh access token (Notion tokens don't expire)

        Args:
            refresh_token: Refresh token (not used by Notion)
            client_id: Notion OAuth client ID
            client_secret: Notion OAuth client secret
            **kwargs: Additional parameters

        Returns:
            Token response (returns original token as Notion tokens don't expire)
        """
        # Notion tokens don't expire, so we just return the existing token
        # This method is here for interface compatibility
        raise NotImplementedError("Notion tokens do not expire and cannot be refreshed")

    async def revoke_token(self, token: str, client_id: str, client_secret: str, **kwargs) -> bool:
        """
        Revoke access token

        Args:
            token: Access token to revoke
            client_id: Notion OAuth client ID
            client_secret: Notion OAuth client secret
            **kwargs: Additional parameters

        Returns:
            True if revocation successful
        """
        # Notion doesn't have a token revocation endpoint
        # Users must revoke access through Notion's UI
        return True

    async def get_user_info(self, access_token: str, **kwargs) -> dict[str, Any]:
        """
        Get authenticated user information

        Args:
            access_token: Valid access token
            **kwargs: Additional parameters

        Returns:
            User information
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",  # Latest stable version
        }

        client = await get_httpx_client()
        # Get bot user info
        response = await client.get("https://api.notion.com/v1/users/me", headers=headers, timeout=30.0)
        response.raise_for_status()
        user_data = response.json()

        return {
            "id": user_data.get("id"),
            "name": user_data.get("name"),
            "avatar_url": user_data.get("avatar_url"),
            "type": user_data.get("type"),
            "email": user_data.get("person", {}).get("email"),
        }

    def validate_token_response(self, token_data: dict[str, Any]) -> bool:
        """
        Validate token response from Notion

        Args:
            token_data: Token response data

        Returns:
            True if valid
        """
        required_fields = ["access_token", "workspace_id"]
        return all(field in token_data for field in required_fields)
