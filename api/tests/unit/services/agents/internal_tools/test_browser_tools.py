"""
Tests for browser_tools.py - Browser Automation

Tests the Playwright browser automation tools including SSRF protection.
"""

from unittest.mock import patch

import pytest

from src.services.agents.internal_tools.browser_tools import BrowserTools


class TestIsInternalIp:
    """Tests for _is_internal_ip SSRF protection."""

    def test_blocks_localhost(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"):
            assert BrowserTools._is_internal_ip("localhost") is True

    def test_blocks_private_class_a(self):
        with patch("socket.gethostbyname", return_value="10.0.0.1"):
            assert BrowserTools._is_internal_ip("internal.server") is True

    def test_blocks_private_class_b(self):
        with patch("socket.gethostbyname", return_value="172.16.0.1"):
            assert BrowserTools._is_internal_ip("internal.server") is True

    def test_blocks_private_class_c(self):
        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            assert BrowserTools._is_internal_ip("internal.server") is True

    def test_blocks_aws_metadata(self):
        with patch("socket.gethostbyname", return_value="169.254.169.254"):
            assert BrowserTools._is_internal_ip("metadata.server") is True

    def test_allows_public_ip(self):
        with patch("socket.gethostbyname", return_value="8.8.8.8"):
            assert BrowserTools._is_internal_ip("google.com") is False

    def test_blocks_unresolvable_hostname(self):
        import socket

        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            assert BrowserTools._is_internal_ip("nonexistent.host") is True


class TestIsUrlAllowed:
    """Tests for _is_url_allowed URL validation."""

    def test_blocks_non_http_schemes(self):
        assert BrowserTools._is_url_allowed("ftp://example.com") is False
        assert BrowserTools._is_url_allowed("file:///etc/passwd") is False

    def test_allows_http_url(self):
        with patch.object(BrowserTools, "_is_internal_ip", return_value=False):
            assert BrowserTools._is_url_allowed("http://example.com") is True

    def test_allows_https_url(self):
        with patch.object(BrowserTools, "_is_internal_ip", return_value=False):
            assert BrowserTools._is_url_allowed("https://example.com") is True

    def test_blocks_internal_ip_url(self):
        with patch.object(BrowserTools, "_is_internal_ip", return_value=True):
            assert BrowserTools._is_url_allowed("https://internal.server") is False

    def test_respects_allowed_domains(self):
        original = BrowserTools.ALLOWED_DOMAINS
        try:
            BrowserTools.ALLOWED_DOMAINS = ["example.com"]
            with patch.object(BrowserTools, "_is_internal_ip", return_value=False):
                assert BrowserTools._is_url_allowed("https://example.com/page") is True
                assert BrowserTools._is_url_allowed("https://evil.com/page") is False
        finally:
            BrowserTools.ALLOWED_DOMAINS = original


class TestNavigateToUrl:
    """Tests for navigate_to_url function."""

    @pytest.mark.asyncio
    async def test_rejects_blocked_url(self):
        with patch.object(BrowserTools, "_is_url_allowed", return_value=False):
            result = await BrowserTools.navigate_to_url("http://internal.server")
            assert result["success"] is False
            assert "not allowed" in result["error"]


class TestExtractLinks:
    """Tests for extract_links function."""

    @pytest.mark.asyncio
    async def test_rejects_blocked_url(self):
        with patch.object(BrowserTools, "_is_url_allowed", return_value=False):
            result = await BrowserTools.extract_links("http://internal.server")
            assert result["success"] is False


class TestExtractStructuredData:
    """Tests for extract_structured_data function."""

    @pytest.mark.asyncio
    async def test_rejects_blocked_url(self):
        with patch.object(BrowserTools, "_is_url_allowed", return_value=False):
            result = await BrowserTools.extract_structured_data("http://internal.server", ".class")
            assert result["success"] is False


class TestCheckElementExists:
    """Tests for check_element_exists function."""

    @pytest.mark.asyncio
    async def test_rejects_blocked_url(self):
        with patch.object(BrowserTools, "_is_url_allowed", return_value=False):
            result = await BrowserTools.check_element_exists("http://internal.server", ".class")
            assert result["success"] is False
