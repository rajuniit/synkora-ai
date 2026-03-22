"""
Unit tests for Google OAuth Service.

Tests OAuth authorization URL generation, token exchange, refresh, and user info.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.oauth.google_oauth import GoogleOAuth


class TestGoogleOAuthInit:
    """Test GoogleOAuth initialization."""

    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        oauth = GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

        assert oauth.client_id == "test_client_id"
        assert oauth.client_secret == "test_client_secret"
        assert oauth.redirect_uri == "https://example.com/callback"

    def test_class_urls(self):
        """Test that class URLs are correctly defined."""
        assert GoogleOAuth._AUTH_URL == "https://accounts.google.com/o/oauth2/v2/auth"
        assert GoogleOAuth._TOKEN_URL == "https://oauth2.googleapis.com/token"
        assert GoogleOAuth._USER_INFO_URL == "https://www.googleapis.com/oauth2/v2/userinfo"
        assert GoogleOAuth._REVOKE_URL == "https://oauth2.googleapis.com/revoke"


class TestFromEnv:
    """Test creating GoogleOAuth from environment variables."""

    def test_from_env_success(self):
        """Test successful creation from environment."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_OAUTH_CLIENT_ID": "env_client_id",
                "GOOGLE_OAUTH_CLIENT_SECRET": "env_client_secret",
                "GOOGLE_OAUTH_REDIRECT_URI": "https://env.example.com/callback",
            },
        ):
            oauth = GoogleOAuth.from_env()

            assert oauth.client_id == "env_client_id"
            assert oauth.client_secret == "env_client_secret"
            assert oauth.redirect_uri == "https://env.example.com/callback"

    def test_from_env_missing_client_id(self):
        """Test error when client ID is missing."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_OAUTH_CLIENT_SECRET": "secret",
            },
            clear=True,
        ):
            with pytest.raises(ValueError) as exc_info:
                GoogleOAuth.from_env()

            assert "environment variables not configured" in str(exc_info.value)

    def test_from_env_missing_client_secret(self):
        """Test error when client secret is missing."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_OAUTH_CLIENT_ID": "client_id",
            },
            clear=True,
        ):
            with pytest.raises(ValueError) as exc_info:
                GoogleOAuth.from_env()

            assert "environment variables not configured" in str(exc_info.value)


class TestGetAuthorizationUrl:
    """Test authorization URL generation."""

    @pytest.fixture
    def oauth(self):
        """Create Google OAuth instance."""
        return GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    def test_default_scopes(self, oauth):
        """Test authorization URL with default scopes."""
        url = oauth.get_authorization_url()

        assert "https://accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert "scope=openid+email+profile" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    def test_custom_scopes(self, oauth):
        """Test authorization URL with custom scopes."""
        url = oauth.get_authorization_url(scopes=["https://www.googleapis.com/auth/calendar"])

        assert "calendar" in url

    def test_with_state(self, oauth):
        """Test authorization URL with state parameter."""
        url = oauth.get_authorization_url(state="random_state_123")

        assert "state=random_state_123" in url

    def test_without_state(self, oauth):
        """Test authorization URL without state parameter."""
        url = oauth.get_authorization_url()

        assert "state=" not in url


class TestGetAccessToken:
    """Test access token exchange."""

    @pytest.fixture
    def oauth(self):
        """Create Google OAuth instance."""
        return GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_token_exchange(self, oauth):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.test_access_token",
            "refresh_token": "1//test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "openid email profile",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.get_access_token("auth_code_123")

            assert result["access_token"] == "ya29.test_access_token"
            assert result["refresh_token"] == "1//test_refresh_token"
            assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self, oauth):
        """Test token exchange failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code was already redeemed.",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            with pytest.raises(ValueError) as exc_info:
                await oauth.get_access_token("invalid_code")

            assert "Failed to get access token" in str(exc_info.value)
            assert "Code was already redeemed" in str(exc_info.value)


class TestGetUserInfo:
    """Test user info retrieval."""

    @pytest.fixture
    def oauth(self):
        """Create Google OAuth instance."""
        return GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_user_info(self, oauth):
        """Test successful user info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "123456789",
            "email": "test@gmail.com",
            "verified_email": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://lh3.googleusercontent.com/photo.jpg",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            user_info = await oauth.get_user_info("test_access_token")

            assert user_info["id"] == "123456789"
            assert user_info["email"] == "test@gmail.com"
            assert user_info["verified_email"] is True
            assert user_info["name"] == "Test User"


class TestRefreshToken:
    """Test token refresh."""

    @pytest.fixture
    def oauth(self):
        """Create Google OAuth instance."""
        return GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_refresh(self, oauth):
        """Test successful token refresh."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.refresh_token("1//refresh_token")

            assert result["access_token"] == "ya29.new_access_token"
            assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_refresh_failure(self, oauth):
        """Test token refresh failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Token has been revoked.",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            with pytest.raises(ValueError) as exc_info:
                await oauth.refresh_token("invalid_refresh_token")

            assert "Failed to refresh token" in str(exc_info.value)


class TestRevokeToken:
    """Test token revocation."""

    @pytest.fixture
    def oauth(self):
        """Create Google OAuth instance."""
        return GoogleOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_revocation(self, oauth):
        """Test successful token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("token_to_revoke")

            assert result is True

    @pytest.mark.asyncio
    async def test_revocation_failure(self, oauth):
        """Test token revocation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("invalid_token")

            assert result is False

    @pytest.mark.asyncio
    async def test_revocation_exception(self, oauth):
        """Test token revocation with exception."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))

        with patch(
            "src.services.oauth.google_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("token")

            assert result is False
