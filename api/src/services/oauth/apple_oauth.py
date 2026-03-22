"""
Apple OAuth Implementation.

Provides OAuth authentication for Apple services (Sign in with Apple).
"""

import logging
import os
import time
import urllib.parse
from typing import Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.social_auth.provider_config_service import SocialAuthProviderConfigService
from .base_oauth import BaseOAuthService
from .http_client import get_httpx_client

logger = logging.getLogger(__name__)


class AppleOAuth(BaseOAuthService):
    """Apple OAuth 2.0 authentication handler."""

    _AUTH_URL = "https://appleid.apple.com/auth/authorize"
    _TOKEN_URL = "https://appleid.apple.com/auth/token"
    _REVOKE_URL = "https://appleid.apple.com/auth/revoke"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        team_id: str | None = None,
        key_id: str | None = None,
        private_key: str | None = None,
    ):
        """
        Initialize Apple OAuth service.

        Args:
            client_id: Apple Services ID
            client_secret: Not used for Apple (generated from private key)
            redirect_uri: Callback URL
            team_id: Apple Team ID (required for client secret generation)
            key_id: Apple Key ID (required for client secret generation)
            private_key: Apple private key content (required for client secret generation)
        """
        super().__init__(client_id, client_secret, redirect_uri)
        self.team_id = team_id
        self.key_id = key_id
        self.private_key = private_key

    @classmethod
    async def from_database(cls, db: AsyncSession, tenant_id: str) -> "AppleOAuth":
        """
        Create AppleOAuth instance from database configuration.

        Args:
            db: Database session
            tenant_id: Tenant ID

        Returns:
            AppleOAuth instance

        Raises:
            ValueError: If configuration not found or incomplete
        """
        from uuid import UUID

        # Convert tenant_id to UUID if it's a string
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        config = await SocialAuthProviderConfigService.get_provider(db, tenant_id, "apple", decrypt_secret=True)

        if not config:
            raise ValueError("Apple OAuth is not configured")

        if config.get("enabled") != "true":
            raise ValueError("Apple OAuth is not enabled")

        if not config.get("client_id"):
            raise ValueError("Apple OAuth configuration is incomplete")

        # For Apple, we need team_id, key_id, and private_key from config
        # These should be stored in the config's metadata or additional fields
        redirect_uri = config.get("redirect_uri") or os.getenv("APPLE_OAUTH_REDIRECT_URI", "")

        return cls(
            client_id=config["client_id"],
            client_secret="",  # Not used for Apple
            redirect_uri=redirect_uri,
            team_id=config.get("client_secret"),  # Temporarily using client_secret field for team_id
            key_id=None,  # Apple Sign In requires key_id - add to SocialAuthConfig if needed
            private_key=None,  # Apple Sign In requires private_key - add to SocialAuthConfig if needed
        )

    @classmethod
    def from_env(cls) -> "AppleOAuth":
        """
        Create AppleOAuth instance from environment variables.

        Returns:
            AppleOAuth instance

        Raises:
            ValueError: If required environment variables are missing
        """
        client_id = os.getenv("APPLE_OAUTH_CLIENT_ID")
        team_id = os.getenv("APPLE_OAUTH_TEAM_ID")
        key_id = os.getenv("APPLE_OAUTH_KEY_ID")
        private_key = os.getenv("APPLE_OAUTH_PRIVATE_KEY")
        redirect_uri = os.getenv("APPLE_OAUTH_REDIRECT_URI", "")

        if not client_id or not team_id or not key_id or not private_key:
            raise ValueError("Apple OAuth environment variables not configured")

        return cls(
            client_id=client_id,
            client_secret="",  # Not used for Apple
            redirect_uri=redirect_uri,
            team_id=team_id,
            key_id=key_id,
            private_key=private_key,
        )

    def _generate_client_secret(self) -> str:
        """
        Generate Apple client secret JWT.

        Returns:
            Client secret JWT

        Raises:
            ValueError: If required parameters are missing
        """
        if not all([self.team_id, self.key_id, self.private_key]):
            raise ValueError("team_id, key_id, and private_key are required for Apple OAuth")

        headers = {
            "kid": self.key_id,
            "alg": "ES256",
        }

        now = int(time.time())
        payload = {
            "iss": self.team_id,
            "iat": now,
            "exp": now + 86400 * 180,  # 6 months
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }

        return jwt.encode(payload, self.private_key, algorithm="ES256", headers=headers)

    def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
        """
        Get the Apple OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth scopes to request (default: name, email)

        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ["name", "email"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "response_mode": "form_post",
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
            Dictionary containing access_token, refresh_token, id_token, etc.

        Raises:
            ValueError: If token exchange fails
        """
        client_secret = self._generate_client_secret()

        data = {
            "client_id": self.client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        client = await get_httpx_client()
        response = await client.post(self._TOKEN_URL, data=data)
        response_json = response.json()

        if "error" in response_json:
            error = response_json.get("error_description", response_json.get("error", "Unknown error"))
            raise ValueError(f"Failed to get access token: {error}")

        return response_json

    async def _get_apple_public_keys(self) -> dict[str, Any]:
        """
        Fetch Apple's public keys for JWT verification.

        Returns:
            JWKS (JSON Web Key Set) from Apple
        """
        client = await get_httpx_client()
        response = await client.get("https://appleid.apple.com/auth/keys", timeout=10)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch Apple public keys: HTTP {response.status_code}")
        return response.json()

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """
        Get user information from ID token with proper signature verification.

        Note: Apple doesn't provide a userinfo endpoint. User info is in the ID token.

        Args:
            token: ID token (not access token)

        Returns:
            User information dictionary with:
            - id: Apple user ID (sub claim)
            - email: User email
            - name: User display name (if provided)
            - email_verified: Whether email is verified

        Raises:
            ValueError: If token is invalid or verification fails
        """
        try:
            # SECURITY: Properly verify the JWT signature using Apple's public keys
            # Fetch Apple's JWKS (JSON Web Key Set)
            jwks = await self._get_apple_public_keys()

            # Get the key ID from the token header
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise ValueError("Token missing 'kid' header")

            # Find the matching public key
            public_key = None
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
                    break

            if not public_key:
                raise ValueError(f"Could not find public key with kid: {kid}")

            # SECURITY: Verify and decode the token with full validation
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer="https://appleid.apple.com",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "require": ["sub", "iss", "aud", "exp"],
                },
            )

            return {
                "id": decoded.get("sub"),
                "email": decoded.get("email"),
                "email_verified": decoded.get("email_verified", False),
                "name": decoded.get("name"),  # Only provided on first sign-in
            }
        except jwt.ExpiredSignatureError:
            logger.error("Apple ID token has expired")
            raise ValueError("ID token has expired")
        except jwt.InvalidAudienceError:
            logger.error("Apple ID token has invalid audience")
            raise ValueError("ID token has invalid audience")
        except jwt.InvalidIssuerError:
            logger.error("Apple ID token has invalid issuer")
            raise ValueError("ID token has invalid issuer")
        except jwt.InvalidSignatureError:
            logger.error("Apple ID token signature verification failed")
            raise ValueError("ID token signature verification failed")
        except Exception as e:
            logger.error(f"Failed to decode Apple ID token: {e}")
            raise ValueError(f"Invalid ID token: {e}")

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dictionary containing new access_token and id_token

        Raises:
            ValueError: If token refresh fails
        """
        client_secret = self._generate_client_secret()

        data = {
            "client_id": self.client_id,
            "client_secret": client_secret,
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
        Revoke an access or refresh token.

        Args:
            token: Access or refresh token to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            client_secret = self._generate_client_secret()

            data = {
                "client_id": self.client_id,
                "client_secret": client_secret,
                "token": token,
                "token_type_hint": "refresh_token",
            }

            client = await get_httpx_client()
            response = await client.post(self._REVOKE_URL, data=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
