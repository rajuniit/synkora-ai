"""
Unit tests for Base OAuth Service.

Tests the abstract base class for OAuth providers.
"""

from abc import ABC
from typing import Any

import pytest

from src.services.oauth.base_oauth import BaseOAuthService


class TestBaseOAuthService:
    """Test BaseOAuthService abstract class."""

    def test_is_abstract_class(self):
        """Test that BaseOAuthService is an abstract class."""
        assert issubclass(BaseOAuthService, ABC)

    def test_cannot_instantiate_directly(self):
        """Test that BaseOAuthService cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseOAuthService(
                client_id="test",
                client_secret="test",
                redirect_uri="https://example.com",
            )

        assert "abstract" in str(exc_info.value).lower()

    def test_concrete_implementation(self):
        """Test that a concrete implementation can be created."""

        class ConcreteOAuth(BaseOAuthService):
            def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
                return f"https://auth.example.com?client_id={self.client_id}"

            async def get_access_token(self, code: str) -> dict[str, Any]:
                return {"access_token": "test_token"}

            async def get_user_info(self, token: str) -> dict[str, Any]:
                return {"id": "123", "email": "test@example.com", "name": "Test"}

            async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
                return {"access_token": "new_token"}

            async def revoke_token(self, token: str) -> bool:
                return True

        oauth = ConcreteOAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="https://example.com/callback",
        )

        assert oauth.client_id == "test_client_id"
        assert oauth.client_secret == "test_client_secret"
        assert oauth.redirect_uri == "https://example.com/callback"

    def test_missing_abstract_methods(self):
        """Test that missing abstract methods raises error."""

        class IncompleteOAuth(BaseOAuthService):
            def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
                return "https://auth.example.com"

            # Missing other abstract methods

        with pytest.raises(TypeError) as exc_info:
            IncompleteOAuth(
                client_id="test",
                client_secret="test",
                redirect_uri="https://example.com",
            )

        # Should mention missing abstract methods
        assert "abstract" in str(exc_info.value).lower()

    def test_init_stores_credentials(self):
        """Test that __init__ stores credentials correctly."""

        class TestOAuth(BaseOAuthService):
            def get_authorization_url(self, state: str | None = None, scopes: list[str] | None = None) -> str:
                return ""

            async def get_access_token(self, code: str) -> dict[str, Any]:
                return {}

            async def get_user_info(self, token: str) -> dict[str, Any]:
                return {}

            async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
                return {}

            async def revoke_token(self, token: str) -> bool:
                return True

        oauth = TestOAuth(
            client_id="my_client_id",
            client_secret="my_secret",
            redirect_uri="https://my.app/callback",
        )

        assert oauth.client_id == "my_client_id"
        assert oauth.client_secret == "my_secret"
        assert oauth.redirect_uri == "https://my.app/callback"


class TestAbstractMethods:
    """Test that abstract methods have correct signatures."""

    def test_get_authorization_url_signature(self):
        """Test get_authorization_url method signature."""
        method = BaseOAuthService.get_authorization_url
        annotations = method.__annotations__

        assert "state" in str(annotations) or "return" in annotations
        assert annotations.get("return") is str

    def test_get_access_token_signature(self):
        """Test get_access_token method signature."""
        method = BaseOAuthService.get_access_token
        annotations = method.__annotations__

        assert "code" in annotations
        assert annotations["code"] is str

    def test_get_user_info_signature(self):
        """Test get_user_info method signature."""
        method = BaseOAuthService.get_user_info
        annotations = method.__annotations__

        assert "token" in annotations
        assert annotations["token"] is str

    def test_refresh_token_signature(self):
        """Test refresh_token method signature."""
        method = BaseOAuthService.refresh_token
        annotations = method.__annotations__

        assert "refresh_token" in annotations
        assert annotations["refresh_token"] is str

    def test_revoke_token_signature(self):
        """Test revoke_token method signature."""
        method = BaseOAuthService.revoke_token
        annotations = method.__annotations__

        assert "token" in annotations
        assert annotations["token"] is str
        assert annotations.get("return") is bool
