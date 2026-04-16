"""
Tests for browser_interactive.py - Interactive Browser Tools

Tests the utility functions and input validation for browser automation tools.
Browser session functions are tested with mocked Playwright objects.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.agents.internal_tools.browser_interactive import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
    _get_locator_strategies,
    _get_workspace_path,
    _resolve_locator,
    _validate_path_in_workspace,
    normalize_timeout,
)


class TestGetWorkspacePath:
    """Tests for _get_workspace_path helper."""

    def test_returns_workspace_from_config(self):
        config = {"workspace_path": "/tmp/workspace"}
        result = _get_workspace_path(config)
        assert result == "/tmp/workspace"

    def test_returns_none_for_empty_config(self):
        result = _get_workspace_path({})
        assert result is None

    def test_returns_none_for_none_config(self):
        result = _get_workspace_path(None)
        assert result is None


class TestValidatePathInWorkspace:
    """Tests for _validate_path_in_workspace function."""

    def test_valid_path_within_workspace(self):
        with tempfile.TemporaryDirectory() as workspace:
            file_path = os.path.join(workspace, "test.txt")
            valid, error = _validate_path_in_workspace(file_path, workspace)
            assert valid is True
            assert error is None

    def test_valid_path_nested_within_workspace(self):
        with tempfile.TemporaryDirectory() as workspace:
            nested_path = os.path.join(workspace, "sub", "dir", "file.txt")
            valid, error = _validate_path_in_workspace(nested_path, workspace)
            assert valid is True
            assert error is None

    def test_path_outside_workspace(self):
        with tempfile.TemporaryDirectory() as workspace:
            outside_path = "/tmp/outside/file.txt"
            valid, error = _validate_path_in_workspace(outside_path, workspace)
            assert valid is False
            assert "outside" in error.lower()

    def test_no_workspace_path(self):
        valid, error = _validate_path_in_workspace("/tmp/file.txt", None)
        assert valid is False
        assert "no workspace" in error.lower()

    def test_workspace_path_itself(self):
        with tempfile.TemporaryDirectory() as workspace:
            valid, error = _validate_path_in_workspace(workspace, workspace)
            assert valid is True
            assert error is None

    def test_path_traversal_attack(self):
        with tempfile.TemporaryDirectory() as workspace:
            traversal_path = os.path.join(workspace, "..", "..", "etc", "passwd")
            valid, error = _validate_path_in_workspace(traversal_path, workspace)
            assert valid is False
            assert "outside" in error.lower()


class TestNormalizeTimeout:
    """Tests for normalize_timeout function."""

    def test_returns_default_for_none(self):
        result = normalize_timeout(None)
        assert result == DEFAULT_TIMEOUT

    def test_returns_custom_default(self):
        result = normalize_timeout(None, default=5000)
        assert result == 5000

    def test_normal_value_passes_through(self):
        result = normalize_timeout(10000)
        assert result == 10000

    def test_clamps_to_minimum(self):
        result = normalize_timeout(100)
        assert result == MIN_TIMEOUT

    def test_clamps_to_maximum(self):
        result = normalize_timeout(999999)
        assert result == MAX_TIMEOUT

    def test_exact_min_boundary(self):
        result = normalize_timeout(MIN_TIMEOUT)
        assert result == MIN_TIMEOUT

    def test_exact_max_boundary(self):
        result = normalize_timeout(MAX_TIMEOUT)
        assert result == MAX_TIMEOUT

    def test_negative_value(self):
        result = normalize_timeout(-1000)
        assert result == MIN_TIMEOUT

    def test_zero_value(self):
        result = normalize_timeout(0)
        assert result == MIN_TIMEOUT


class TestGetLocatorStrategies:
    """Tests for _get_locator_strategies function."""

    def test_css_selector_strategy(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator

        strategies = _get_locator_strategies(mock_page, "#submit-btn")

        # Should create CSS and text-based strategies
        assert len(strategies) > 0

    def test_stored_ref_with_state(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.first = MagicMock()
        mock_page.locator.return_value = mock_locator
        mock_page.get_by_role.return_value = mock_locator

        # Create mock state with stored element ref
        mock_state = MagicMock()
        mock_element_ref = MagicMock()
        mock_element_ref.selector = "#my-button"
        mock_element_ref.role = "button"
        mock_element_ref.name = "Submit"
        mock_element_ref.nth = 0
        mock_state.element_refs = {"e1": mock_element_ref}

        strategies = _get_locator_strategies(mock_page, "e1", mock_state)

        # Should find stored ref and create strategies
        assert len(strategies) >= 1

    def test_unstored_ref_without_state(self):
        mock_page = MagicMock()
        mock_page.locator.return_value = MagicMock()

        strategies = _get_locator_strategies(mock_page, "e1")

        # Without state, "e1" won't match stored refs
        # Should still create fallback strategies
        assert isinstance(strategies, list)


class TestResolveLocator:
    """Tests for _resolve_locator function."""

    def test_returns_first_strategy(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator

        # With a CSS selector, should return a locator
        result = _resolve_locator(mock_page, "#my-element")

        assert result is not None

    def test_falls_back_to_css_selector(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator

        result = _resolve_locator(mock_page, "div.my-class")

        # Should fall back to page.locator(ref)
        assert result is not None


def _make_scraper_mock(side_effect=None, return_value=None):
    """Return a mock _scraper() that raises or returns as specified."""
    mock_client = AsyncMock()
    if side_effect is not None:
        for attr in (
            "browser_navigate",
            "browser_click",
            "browser_screenshot",
            "browser_get_cookies",
            "browser_clear_cookies",
            "browser_list_pages",
            "browser_close_session",
        ):
            getattr(mock_client, attr).side_effect = side_effect
    elif return_value is not None:
        for attr in (
            "browser_navigate",
            "browser_click",
            "browser_screenshot",
            "browser_get_cookies",
            "browser_clear_cookies",
            "browser_list_pages",
            "browser_close_session",
        ):
            getattr(mock_client, attr).return_value = return_value
    return mock_client


class TestBrowserNavigate:
    """Tests for internal_browser_navigate function."""

    @pytest.mark.asyncio
    async def test_navigate_success(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_navigate

        mock_result = {"success": True, "url": "https://example.com", "title": "Example", "status": 200}
        mock_client = AsyncMock()
        mock_client.browser_navigate.return_value = mock_result

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_navigate(url="https://example.com")

        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example"
        assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_navigate_error(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_navigate

        mock_client = AsyncMock()
        mock_client.browser_navigate.side_effect = Exception("Connection refused")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_navigate(url="https://slow-site.com")

        assert result["success"] is False
        assert "error" in result


class TestBrowserClick:
    """Tests for internal_browser_click function."""

    @pytest.mark.asyncio
    async def test_click_error_handling(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_click

        mock_client = AsyncMock()
        mock_client.browser_click.side_effect = Exception("Session error")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_click(ref="#submit-btn")

        assert result["success"] is False
        assert "error" in result


class TestBrowserScreenshot:
    """Tests for internal_browser_screenshot function."""

    @pytest.mark.asyncio
    async def test_screenshot_requires_session(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_screenshot

        mock_client = AsyncMock()
        mock_client.browser_screenshot.side_effect = Exception("Session not found")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_screenshot()

        assert result["success"] is False


class TestBrowserCookies:
    """Tests for browser cookie management functions."""

    @pytest.mark.asyncio
    async def test_get_cookies_error_handling(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_get_cookies

        mock_client = AsyncMock()
        mock_client.browser_get_cookies.side_effect = Exception("No session")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_get_cookies()

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_clear_cookies_error_handling(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_clear_cookies

        mock_client = AsyncMock()
        mock_client.browser_clear_cookies.side_effect = Exception("No session")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_clear_cookies()

        assert result["success"] is False


class TestBrowserPageManagement:
    """Tests for browser page management functions."""

    @pytest.mark.asyncio
    async def test_list_pages_error_handling(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_list_pages

        mock_client = AsyncMock()
        mock_client.browser_list_pages.side_effect = Exception("No session")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_list_pages()

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_close_session_error_handling(self):
        from src.services.agents.internal_tools.browser_interactive import internal_browser_close_session

        mock_client = AsyncMock()
        mock_client.browser_close_session.side_effect = Exception("Session close error")

        with patch("src.services.agents.internal_tools.browser_interactive._scraper", return_value=mock_client):
            result = await internal_browser_close_session()

        assert result["success"] is False
        assert "Session close error" in result["error"]
