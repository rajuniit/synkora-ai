"""
Unit tests for GitHub OAuth Service.

Tests OAuth authorization URL generation, token exchange, and user info retrieval.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.oauth.github_oauth import GitHubOAuth


class TestGitHubOAuthInit:
    """Test GitHubOAuth initialization."""

    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        oauth = GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

        assert oauth.client_id == "test_client_id"
        assert oauth.client_secret == "test_client_secret"
        assert oauth.redirect_uri == "https://example.com/callback"

    def test_class_urls(self):
        """Test that class URLs are correctly defined."""
        assert GitHubOAuth._AUTH_URL == "https://github.com/login/oauth/authorize"
        assert GitHubOAuth._TOKEN_URL == "https://github.com/login/oauth/access_token"
        assert GitHubOAuth._USER_INFO_URL == "https://api.github.com/user"
        assert GitHubOAuth._EMAIL_INFO_URL == "https://api.github.com/user/emails"


class TestGetAuthorizationUrl:
    """Test authorization URL generation."""

    @pytest.fixture
    def oauth(self):
        """Create GitHub OAuth instance."""
        return GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    def test_default_scopes(self, oauth):
        """Test authorization URL with default scopes."""
        url = oauth.get_authorization_url()

        assert "https://github.com/login/oauth/authorize" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in url
        assert "scope=repo+user+read%3Aorg" in url

    def test_custom_scopes(self, oauth):
        """Test authorization URL with custom scopes."""
        url = oauth.get_authorization_url(scopes=["user", "public_repo"])

        assert "scope=user+public_repo" in url

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
        """Create GitHub OAuth instance."""
        return GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_token_exchange(self, oauth):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "gho_test_token_123"}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            token = await oauth.get_access_token("auth_code_123")

            assert token == "gho_test_token_123"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self, oauth):
        """Test token exchange failure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            with pytest.raises(ValueError) as exc_info:
                await oauth.get_access_token("invalid_code")

            assert "Failed to get access token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_token_exchange_error_without_description(self, oauth):
        """Test token exchange error without description."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "access_denied"}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            with pytest.raises(ValueError) as exc_info:
                await oauth.get_access_token("code")

            assert "access_denied" in str(exc_info.value)


class TestGetUserInfo:
    """Test user info retrieval."""

    @pytest.fixture
    def oauth(self):
        """Create GitHub OAuth instance."""
        return GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_user_info(self, oauth):
        """Test successful user info retrieval."""
        user_response = MagicMock()
        user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": None,
            "avatar_url": "https://github.com/avatar.png",
        }
        user_response.raise_for_status = MagicMock()

        email_response = MagicMock()
        email_response.status_code = 200
        email_response.json.return_value = [
            {"email": "test@example.com", "primary": True, "verified": True},
            {"email": "other@example.com", "primary": False, "verified": True},
        ]

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[user_response, email_response])

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            user_info = await oauth.get_user_info("test_token")

            assert user_info["id"] == 12345
            assert user_info["login"] == "testuser"
            assert user_info["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_user_info_with_email_permission_denied(self, oauth):
        """Test user info when email permission is denied."""
        user_response = MagicMock()
        user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "email": "public@example.com",
        }
        user_response.raise_for_status = MagicMock()

        email_response = MagicMock()
        email_response.status_code = 403

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[user_response, email_response])

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            user_info = await oauth.get_user_info("test_token")

            assert user_info["email"] == "public@example.com"

    @pytest.mark.asyncio
    async def test_user_info_email_fetch_exception(self, oauth):
        """Test user info when email fetch throws exception."""
        user_response = MagicMock()
        user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "email": "fallback@example.com",
        }
        user_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=[user_response, Exception("Network error")])

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            user_info = await oauth.get_user_info("test_token")

            assert user_info["email"] == "fallback@example.com"


class TestRefreshToken:
    """Test token refresh."""

    @pytest.fixture
    def oauth(self):
        """Create GitHub OAuth instance."""
        return GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_refresh_returns_same_token(self, oauth):
        """Test that refresh returns same token (GitHub tokens don't expire)."""
        token = await oauth.refresh_token("original_token")

        assert token == "original_token"


class TestRevokeToken:
    """Test token revocation."""

    @pytest.fixture
    def oauth(self):
        """Create GitHub OAuth instance."""
        return GitHubOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

    @pytest.mark.asyncio
    async def test_successful_revocation(self, oauth):
        """Test successful token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("token_to_revoke")

            assert result is True

    @pytest.mark.asyncio
    async def test_revocation_failure(self, oauth):
        """Test token revocation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=mock_response)

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("invalid_token")

            assert result is False

    @pytest.mark.asyncio
    async def test_revocation_exception(self, oauth):
        """Test token revocation with exception."""
        mock_client = MagicMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Network error"))

        with patch(
            "src.services.oauth.github_oauth.get_httpx_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ):
            result = await oauth.revoke_token("token")

            assert result is False
