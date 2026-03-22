"""
Base OAuth Service.

Provides a common interface for OAuth 2.0 authentication providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseOAuthService(ABC):
    """Base class for OAuth 2.0 authentication services."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize OAuth service.

        Args:
            client_id: OAuth app client ID
            client_secret: OAuth app client secret
            redirect_uri: Callback URL for OAuth flow
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request

        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    async def get_access_token(self, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dictionary containing access_token and optionally refresh_token, expires_in, etc.

        Raises:
            ValueError: If token exchange fails
        """
        pass

    @abstractmethod
    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information using access token.

        Args:
            token: OAuth access token

        Returns:
            User information dictionary with at minimum:
            - id: Provider-specific user ID
            - email: User email
            - name: User display name
            - picture: Optional profile picture URL
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary containing new access_token and optionally refresh_token, expires_in, etc.

        Raises:
            ValueError: If token refresh fails
        """
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access token.

        Args:
            token: Access token to revoke

        Returns:
            True if successful, False otherwise
        """
        pass
