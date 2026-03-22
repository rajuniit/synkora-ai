"""
Tests for onepassword_tools.py - 1Password SDK Tools

Tests the 1Password integration for secrets, vaults, and items.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the onepassword SDK modules
sys.modules["onepassword"] = MagicMock()
sys.modules["onepassword.client"] = MagicMock()
sys.modules["onepassword.types"] = MagicMock()


class TestInternal1passwordReadSecret:
    """Tests for internal_1password_read_secret function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_read_secret

        result = await internal_1password_read_secret(reference="op://vault/item/field", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordListVaults:
    """Tests for internal_1password_list_vaults function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_list_vaults

        result = await internal_1password_list_vaults(runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordListItems:
    """Tests for internal_1password_list_items function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_list_items

        result = await internal_1password_list_items(runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordGetItem:
    """Tests for internal_1password_get_item function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_get_item

        result = await internal_1password_get_item(vault_id="v1", item_id="i1", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordCreateItem:
    """Tests for internal_1password_create_item function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_create_item

        result = await internal_1password_create_item(vault_id="v1", title="Test", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordUpdateItem:
    """Tests for internal_1password_update_item function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_update_item

        result = await internal_1password_update_item(vault_id="v1", item_id="i1", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordDeleteItem:
    """Tests for internal_1password_delete_item function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_delete_item

        result = await internal_1password_delete_item(vault_id="v1", item_id="i1", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordArchiveItem:
    """Tests for internal_1password_archive_item function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_archive_item

        result = await internal_1password_archive_item(vault_id="v1", item_id="i1", runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordGeneratePassword:
    """Tests for internal_1password_generate_password function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_generate_password

        result = await internal_1password_generate_password(runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternal1passwordResolveMultiple:
    """Tests for internal_1password_resolve_multiple function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.onepassword_tools import internal_1password_resolve_multiple

        result = await internal_1password_resolve_multiple(references=["op://v/i/f"], runtime_context=None)
        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestGet1passwordApp:
    """Tests for _get_1password_app helper function."""

    def test_finds_onepassword_app_from_dict_context(self):
        from src.services.agents.internal_tools.onepassword_tools import _get_1password_app

        ctx = {"oauth_apps": [{"provider": "onepassword", "api_token": "abc"}]}
        result = _get_1password_app(ctx)
        assert result is not None
        assert result["provider"] == "onepassword"

    def test_returns_none_when_no_onepassword_app(self):
        from src.services.agents.internal_tools.onepassword_tools import _get_1password_app

        ctx = {"oauth_apps": [{"provider": "github"}]}
        result = _get_1password_app(ctx)
        assert result is None

    def test_returns_none_for_empty_context(self):
        from src.services.agents.internal_tools.onepassword_tools import _get_1password_app

        result = _get_1password_app(None)
        assert result is None
