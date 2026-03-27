"""Unit tests for ip_utils — get_client_ip and is_trusted_proxy."""

import pytest


@pytest.mark.unit
class TestIsTrustedProxy:
    def test_loopback_ipv4(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("127.0.0.1") is True

    def test_loopback_ipv6(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("::1") is True

    def test_rfc1918_class_a(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("10.0.0.1") is True
        assert is_trusted_proxy("10.255.255.254") is True

    def test_rfc1918_class_b(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("172.16.0.1") is True
        assert is_trusted_proxy("172.31.255.254") is True

    def test_rfc1918_class_c(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("192.168.0.1") is True
        assert is_trusted_proxy("192.168.255.254") is True

    def test_docker_bridge(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("172.17.0.1") is True

    def test_public_ip_not_trusted(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("8.8.8.8") is False
        assert is_trusted_proxy("1.2.3.4") is False

    def test_invalid_string_returns_false(self):
        from src.utils.ip_utils import is_trusted_proxy

        assert is_trusted_proxy("not-an-ip") is False
        assert is_trusted_proxy("") is False


@pytest.mark.unit
class TestGetClientIp:
    def test_direct_public_connection_returns_direct_ip(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("8.8.8.8", None, None)
        assert result == "8.8.8.8"

    def test_direct_public_ignores_forwarded_header(self):
        from src.utils.ip_utils import get_client_ip

        # Public direct connection — XFF should be ignored
        result = get_client_ip("8.8.8.8", "1.2.3.4, 5.6.7.8", None)
        assert result == "8.8.8.8"

    def test_trusted_proxy_uses_xff(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("127.0.0.1", "203.0.113.5", None)
        assert result == "203.0.113.5"

    def test_trusted_proxy_rightmost_non_trusted(self):
        from src.utils.ip_utils import get_client_ip

        # Client: 203.0.113.5, then it went through two proxies 10.0.0.1 and 127.0.0.1
        result = get_client_ip("127.0.0.1", "203.0.113.5, 10.0.0.1", None)
        assert result == "203.0.113.5"

    def test_spoofed_xff_returns_rightmost_non_trusted(self):
        from src.utils.ip_utils import get_client_ip

        # Attacker prepended fake IPs; rightmost non-trusted is the real client
        result = get_client_ip("10.0.0.1", "1.1.1.1, 203.0.113.99, 10.0.0.2", None)
        assert result == "203.0.113.99"

    def test_all_trusted_in_chain_falls_back_to_leftmost(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("127.0.0.1", "10.0.0.1, 192.168.1.1", None)
        assert result == "10.0.0.1"

    def test_real_ip_header_used_when_no_xff(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("127.0.0.1", None, "203.0.113.42")
        assert result == "203.0.113.42"

    def test_xff_takes_precedence_over_real_ip(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("10.0.0.1", "203.0.113.5", "9.9.9.9")
        assert result == "203.0.113.5"

    def test_unknown_direct_ip_returned_as_is(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("unknown", "203.0.113.5", None)
        assert result == "unknown"

    def test_invalid_ip_in_xff_is_skipped(self):
        from src.utils.ip_utils import get_client_ip

        # Invalid entry in XFF should be skipped; valid public one should be used
        result = get_client_ip("127.0.0.1", "not-valid, 203.0.113.7", None)
        assert result == "203.0.113.7"

    def test_invalid_real_ip_falls_back_to_direct(self):
        from src.utils.ip_utils import get_client_ip

        result = get_client_ip("10.0.0.1", None, "INVALID")
        assert result == "10.0.0.1"
