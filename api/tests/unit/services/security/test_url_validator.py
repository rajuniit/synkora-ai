"""
Unit tests for URL Validator.

Tests SSRF protection, IP validation, and URL scheme validation.
"""

import pytest

from src.services.security.url_validator import (
    BLOCKED_HOSTNAMES,
    CLOUD_METADATA_IPS,
    PRIVATE_IP_RANGES,
    SSRFError,
    is_private_ip,
    resolve_hostname,
    validate_url,
    validate_url_for_openapi_import,
    validate_url_for_webhook,
    validate_url_strict,
)


class TestIsPrivateIP:
    """Test private IP detection."""

    def test_localhost_is_private(self):
        """Test that localhost is detected as private."""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.0.0.2") is True

    def test_class_a_private_range(self):
        """Test Class A private range detection."""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True

    def test_class_b_private_range(self):
        """Test Class B private range detection."""
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True

    def test_class_c_private_range(self):
        """Test Class C private range detection."""
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True

    def test_link_local_is_private(self):
        """Test link-local addresses are private."""
        assert is_private_ip("169.254.0.1") is True
        assert is_private_ip("169.254.169.254") is True  # AWS metadata

    def test_public_ip_is_not_private(self):
        """Test that public IPs are not private."""
        assert is_private_ip("8.8.8.8") is False  # Google DNS
        assert is_private_ip("1.1.1.1") is False  # Cloudflare DNS
        assert is_private_ip("142.250.185.46") is False  # google.com

    def test_invalid_ip_returns_false(self):
        """Test that invalid IP addresses return False."""
        assert is_private_ip("not-an-ip") is False
        assert is_private_ip("256.256.256.256") is False
        assert is_private_ip("") is False

    def test_ipv6_loopback_is_private(self):
        """Test IPv6 loopback is private."""
        assert is_private_ip("::1") is True

    def test_ipv6_unique_local_is_private(self):
        """Test IPv6 unique local addresses are private."""
        assert is_private_ip("fc00::1") is True
        assert is_private_ip("fd00::1") is True


class TestResolveHostname:
    """Test hostname resolution."""

    def test_resolve_localhost(self):
        """Test resolving localhost."""
        ips = resolve_hostname("localhost")
        assert len(ips) > 0
        assert any(ip in ["127.0.0.1", "::1"] for ip in ips)

    def test_resolve_invalid_hostname(self):
        """Test resolving invalid hostname returns empty list."""
        ips = resolve_hostname("this-hostname-definitely-does-not-exist-12345.invalid")
        assert ips == []


class TestValidateUrl:
    """Test URL validation."""

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs pass."""
        is_valid, error = validate_url("https://example.com/path")

        assert is_valid is True
        assert error is None

    def test_valid_http_url(self):
        """Test that valid HTTP URLs pass."""
        is_valid, error = validate_url("http://example.com/path")

        assert is_valid is True
        assert error is None

    def test_invalid_scheme_blocked(self):
        """Test that invalid schemes are blocked."""
        is_valid, error = validate_url("ftp://example.com/file")

        assert is_valid is False
        assert "scheme" in error.lower()

    def test_file_scheme_blocked(self):
        """Test that file:// scheme is blocked."""
        is_valid, error = validate_url("file:///etc/passwd")

        assert is_valid is False

    def test_localhost_blocked(self):
        """Test that localhost is blocked."""
        is_valid, error = validate_url("http://localhost/admin")

        assert is_valid is False
        assert "not allowed" in error.lower()

    def test_127_0_0_1_blocked(self):
        """Test that 127.0.0.1 is blocked."""
        is_valid, error = validate_url("http://127.0.0.1/")

        assert is_valid is False

    def test_private_ip_blocked(self):
        """Test that private IPs are blocked."""
        private_urls = [
            "http://10.0.0.1/",
            "http://172.16.0.1/",
            "http://192.168.1.1/",
        ]

        for url in private_urls:
            is_valid, error = validate_url(url)
            assert is_valid is False, f"URL {url} should be blocked"

    def test_cloud_metadata_blocked(self):
        """Test that cloud metadata IPs are blocked."""
        is_valid, error = validate_url("http://169.254.169.254/latest/meta-data/")

        assert is_valid is False
        assert "metadata" in error.lower() or "private" in error.lower()

    def test_url_without_hostname(self):
        """Test URL without hostname is rejected."""
        is_valid, error = validate_url("http:///path")

        assert is_valid is False
        assert "hostname" in error.lower()

    def test_allowed_domains_whitelist(self):
        """Test allowed domains whitelist."""
        is_valid, error = validate_url("https://api.github.com/repos", allowed_domains=["api.github.com", "github.com"])

        assert is_valid is True

    def test_domain_not_in_whitelist_blocked(self):
        """Test domain not in whitelist is blocked."""
        is_valid, error = validate_url("https://evil.com/", allowed_domains=["github.com"])

        assert is_valid is False
        assert "not in the allowed list" in error.lower()

    def test_subdomain_allowed_when_parent_whitelisted(self):
        """Test subdomain is allowed when parent domain is whitelisted."""
        is_valid, error = validate_url("https://api.github.com/", allowed_domains=["github.com"])

        assert is_valid is True

    def test_blocked_ports(self):
        """Test that common internal ports are blocked."""
        blocked_port_urls = [
            "http://example.com:22/",  # SSH
            "http://example.com:3306/",  # MySQL
            "http://example.com:5432/",  # PostgreSQL
            "http://example.com:6379/",  # Redis
            "http://example.com:27017/",  # MongoDB
        ]

        for url in blocked_port_urls:
            is_valid, error = validate_url(url)
            assert is_valid is False, f"Port in {url} should be blocked"

    def test_allowed_ports(self):
        """Test that standard HTTP ports are allowed."""
        is_valid, error = validate_url("https://example.com:443/")
        assert is_valid is True

        is_valid, error = validate_url("http://example.com:80/")
        assert is_valid is True

    def test_custom_allowed_schemes(self):
        """Test custom allowed schemes."""
        is_valid, error = validate_url("ftp://example.com/file", allowed_schemes=["ftp", "ftps"])

        assert is_valid is True

    def test_dns_resolution_disabled(self):
        """Test URL validation with DNS resolution disabled."""
        # When DNS resolution is disabled, we can't check if hostname resolves to private IP
        is_valid, error = validate_url("http://example.com/", resolve_dns=False)

        assert is_valid is True


class TestValidateUrlStrict:
    """Test strict URL validation."""

    def test_only_https_allowed(self):
        """Test that only HTTPS is allowed in strict mode."""
        is_valid_https, _ = validate_url_strict("https://example.com/")
        is_valid_http, error = validate_url_strict("http://example.com/")

        assert is_valid_https is True
        assert is_valid_http is False
        assert "scheme" in error.lower()


class TestValidateUrlForWebhook:
    """Test webhook URL validation."""

    def test_both_http_and_https_allowed(self):
        """Test that both HTTP and HTTPS are allowed for webhooks."""
        is_valid_https, _ = validate_url_for_webhook("https://webhook.example.com/")
        is_valid_http, _ = validate_url_for_webhook("http://webhook.example.com/")

        assert is_valid_https is True
        assert is_valid_http is True

    def test_private_ips_blocked(self):
        """Test that private IPs are blocked for webhooks."""
        is_valid, error = validate_url_for_webhook("http://192.168.1.1/webhook")

        assert is_valid is False


class TestValidateUrlForOpenAPIImport:
    """Test OpenAPI import URL validation."""

    def test_only_https_allowed(self):
        """Test that only HTTPS is allowed for OpenAPI imports."""
        is_valid_https, _ = validate_url_for_openapi_import("https://api.example.com/openapi.json")
        is_valid_http, error = validate_url_for_openapi_import("http://api.example.com/openapi.json")

        assert is_valid_https is True
        assert is_valid_http is False


class TestSSRFError:
    """Test SSRFError exception."""

    def test_ssrf_error_can_be_raised(self):
        """Test that SSRFError can be raised."""
        with pytest.raises(SSRFError):
            raise SSRFError("SSRF attempt detected")


class TestBlockedHostnames:
    """Test blocked hostnames list."""

    def test_localhost_in_blocklist(self):
        """Test that localhost is in blocklist."""
        assert "localhost" in BLOCKED_HOSTNAMES

    def test_metadata_hostnames_blocked(self):
        """Test that cloud metadata hostnames are blocked."""
        assert "metadata.google.internal" in BLOCKED_HOSTNAMES

    def test_kubernetes_hostnames_blocked(self):
        """Test that Kubernetes internal hostnames are blocked."""
        assert "kubernetes.default" in BLOCKED_HOSTNAMES


class TestCloudMetadataIPs:
    """Test cloud metadata IP list."""

    def test_aws_metadata_ip_present(self):
        """Test that AWS metadata IP is in the list."""
        assert "169.254.169.254" in CLOUD_METADATA_IPS


class TestPrivateIPRanges:
    """Test private IP ranges list."""

    def test_private_ranges_defined(self):
        """Test that private IP ranges are defined."""
        assert len(PRIVATE_IP_RANGES) > 0

    def test_loopback_range_included(self):
        """Test that loopback range is included."""
        from ipaddress import ip_network

        loopback = ip_network("127.0.0.0/8")
        assert loopback in PRIVATE_IP_RANGES
