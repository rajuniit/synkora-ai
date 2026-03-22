"""Tests for security_middleware.py.

These tests verify the security middleware functionality including:
- Security headers
- Rate limiting
- Input sanitization
"""

import re
from unittest.mock import AsyncMock, Mock

import pytest


class TestInputSanitizationMiddleware:
    """Tests for InputSanitizationMiddleware."""

    def test_contains_xss_script_detection(self):
        """Test that partial script tags are detected as XSS."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        # Script tag without closing should be detected
        assert middleware._contains_xss('<script type="text/javascript">') is True
        # Full script tag should also be detected
        assert middleware._contains_xss("<script>alert(1)</script>") is True


class TestInputSanitizationMiddlewareLogic:
    """Tests for InputSanitizationMiddleware logic methods."""

    def test_contains_xss_script_tag(self):
        """Test _contains_xss detects script tags."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss("<script>alert(1)</script>") is True
        assert middleware._contains_xss("<SCRIPT>alert(1)</SCRIPT>") is True
        assert middleware._contains_xss('<script type="text/javascript">code</script>') is True

    def test_contains_xss_javascript_protocol(self):
        """Test _contains_xss detects javascript: protocol."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss('href="javascript:alert(1)"') is True
        assert middleware._contains_xss("JavaScript:void(0)") is True
        assert middleware._contains_xss('src="javascript:evil()"') is True

    def test_contains_xss_event_handlers(self):
        """Test _contains_xss detects event handlers."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss('onerror="alert(1)"') is True
        assert middleware._contains_xss('onclick = "evil()"') is True
        assert middleware._contains_xss('onload="hack()"') is True
        assert middleware._contains_xss('onmouseover="bad()"') is True

    def test_contains_xss_iframe(self):
        """Test _contains_xss detects iframe tags."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss('<iframe src="evil.com"></iframe>') is True
        assert middleware._contains_xss("<IFRAME>content</IFRAME>") is True

    def test_contains_xss_object_embed(self):
        """Test _contains_xss detects object and embed tags."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss('<object data="malware.swf"></object>') is True
        assert middleware._contains_xss('<embed src="malware.swf">') is True

    def test_contains_xss_link_meta(self):
        """Test _contains_xss behavior for link and meta tags.

        Bare <link> and <meta> tags are intentionally NOT blocked — they cause
        false positives when users paste HTML snippets or AI responses contain
        HTML examples. Dangerous variants (javascript: URIs, event handlers)
        are caught by the URI-scheme and on*= patterns already in the list.
        """
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        # Safe bare tags — intentionally allowed
        assert middleware._contains_xss('<link rel="stylesheet" href="styles.css">') is False
        assert middleware._contains_xss('<meta http-equiv="refresh">') is False

        # Dangerous variants — caught by existing URI-scheme / event-handler patterns
        assert middleware._contains_xss('<link href="javascript:alert(1)">') is True
        assert middleware._contains_xss('<meta content="0;url=javascript:alert(1)">') is True
        assert middleware._contains_xss('<link onload="alert(1)">') is True

    def test_contains_xss_clean_content(self):
        """Test _contains_xss allows clean content."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert middleware._contains_xss("Hello world") is False
        assert middleware._contains_xss('{"key": "value"}') is False
        assert middleware._contains_xss("Normal <b>bold</b> text") is False
        assert middleware._contains_xss("<p>Paragraph</p>") is False

    def test_get_client_ip_from_forwarded_for(self):
        """Test get_client_ip extracts from X-Forwarded-For via trusted proxy."""
        from src.utils.ip_utils import get_client_ip

        # Direct connection from trusted proxy; X-Forwarded-For carries the real client.
        ip = get_client_ip("127.0.0.1", "203.0.113.4, 10.0.0.1", None)
        assert ip == "203.0.113.4"

    def test_get_client_ip_from_real_ip(self):
        """Test get_client_ip extracts from X-Real-IP via trusted proxy."""
        from src.utils.ip_utils import get_client_ip

        ip = get_client_ip("10.0.0.1", None, "203.0.113.40")
        assert ip == "203.0.113.40"


class TestMiddlewareConstants:
    """Tests for middleware class constants and configurations."""

    def test_xss_patterns_exist(self):
        """Test XSS patterns are defined."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        assert hasattr(middleware, "XSS_PATTERNS")
        assert len(middleware.XSS_PATTERNS) > 0

    def test_xss_patterns_are_valid_regex(self):
        """Test XSS pattern strings are valid and the combined regex compiles."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())

        for pattern in middleware.XSS_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

        # Combined compiled regex must exist and be a Pattern object
        assert isinstance(middleware._XSS_RE, re.Pattern)

    def test_scan_limit_is_set(self):
        """Test that the scan limit constant is defined."""
        from src.middleware.security_middleware import InputSanitizationMiddleware

        middleware = InputSanitizationMiddleware(Mock())
        assert isinstance(middleware._SCAN_LIMIT, int)
        assert middleware._SCAN_LIMIT > 0
