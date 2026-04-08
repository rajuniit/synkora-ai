"""
URL Validation Security Module.

Provides SSRF (Server-Side Request Forgery) protection by validating URLs
before making HTTP requests.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Private/internal IP ranges that should be blocked
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (includes AWS metadata)
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
]

# Blocked hostnames
BLOCKED_HOSTNAMES = [
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "metadata.google.internal",  # GCP metadata
    "metadata.google",
    "metadata",
    "kubernetes.default",  # Kubernetes
    "kubernetes.default.svc",
    "kubernetes.default.svc.cluster.local",
]

# Cloud metadata IP addresses
CLOUD_METADATA_IPS = [
    "169.254.169.254",  # AWS, GCP, Azure, DigitalOcean, etc.
    "169.254.170.2",  # AWS ECS task metadata
    "fd00:ec2::254",  # AWS IPv6 metadata
]


class SSRFError(Exception):
    """Exception raised when SSRF protection blocks a request."""

    pass


def is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address is private/internal.

    Args:
        ip_str: IP address string

    Returns:
        True if IP is private/internal, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        # Invalid IP address format
        return False


def resolve_hostname(hostname: str) -> list[str]:
    """
    Resolve a hostname to IP addresses.

    Args:
        hostname: Hostname to resolve

    Returns:
        List of resolved IP addresses
    """
    try:
        # Get all IP addresses for the hostname
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        ips = list({info[4][0] for info in addr_info})
        return ips
    except socket.gaierror:
        return []


def validate_url(
    url: str,
    allowed_schemes: list[str] | None = None,
    allowed_domains: list[str] | None = None,
    block_private_ips: bool = True,
    resolve_dns: bool = True,
) -> tuple[bool, str | None]:
    """
    Validate a URL for SSRF protection.

    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        allowed_domains: Optional list of allowed domains (if set, only these are allowed)
        block_private_ips: Whether to block private/internal IP addresses
        resolve_dns: Whether to resolve DNS and check resolved IPs

    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme.lower() not in allowed_schemes:
            return False, f"URL scheme '{parsed.scheme}' is not allowed. Allowed: {allowed_schemes}"

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            return False, "URL has no hostname"

        # Normalize hostname
        hostname_lower = hostname.lower()

        # Check against blocked hostnames
        if hostname_lower in BLOCKED_HOSTNAMES:
            logger.warning(f"SSRF blocked: hostname '{hostname}' is in blocklist")
            return False, f"Hostname '{hostname}' is not allowed"

        # Check if hostname is a cloud metadata IP
        if hostname in CLOUD_METADATA_IPS:
            logger.warning(f"SSRF blocked: cloud metadata IP '{hostname}'")
            return False, "Cloud metadata endpoints are not allowed"

        # Check if allowed_domains is set and hostname matches
        if allowed_domains:
            domain_allowed = False
            for allowed in allowed_domains:
                if hostname_lower == allowed.lower():
                    domain_allowed = True
                    break
                # Check subdomain match
                if hostname_lower.endswith("." + allowed.lower()):
                    domain_allowed = True
                    break

            if not domain_allowed:
                return False, f"Domain '{hostname}' is not in the allowed list"

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if block_private_ips and is_private_ip(hostname):
                logger.warning(f"SSRF blocked: private IP '{hostname}'")
                return False, "Private/internal IP addresses are not allowed"
            # Direct IP access is allowed if not private
        except ValueError:
            # Not an IP address, it's a hostname - resolve it if requested
            if resolve_dns and block_private_ips:
                resolved_ips = resolve_hostname(hostname)
                for ip in resolved_ips:
                    if is_private_ip(ip):
                        logger.warning(f"SSRF blocked: hostname '{hostname}' resolves to private IP '{ip}'")
                        return False, "Hostname resolves to a private/internal IP address"

                    if ip in CLOUD_METADATA_IPS:
                        logger.warning(f"SSRF blocked: hostname '{hostname}' resolves to cloud metadata IP '{ip}'")
                        return False, "Hostname resolves to a cloud metadata endpoint"

        # Check port
        port = parsed.port
        if port:
            # Block common internal service ports
            blocked_ports = [
                22,  # SSH
                23,  # Telnet
                25,  # SMTP
                53,  # DNS
                135,  # RPC
                137,
                138,
                139,  # NetBIOS
                445,  # SMB
                3306,  # MySQL
                5432,  # PostgreSQL
                6379,  # Redis
                27017,  # MongoDB
                11211,  # Memcached
            ]
            if port in blocked_ports and not allowed_domains:
                logger.warning(f"SSRF blocked: port {port} is blocked")
                return False, f"Port {port} is not allowed for external requests"

        return True, None

    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False, f"Invalid URL: {str(e)}"


def validate_url_strict(url: str) -> tuple[bool, str | None]:
    """
    Strict URL validation - blocks all private IPs and resolves DNS.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_url(
        url,
        allowed_schemes=["https"],  # Only HTTPS
        block_private_ips=True,
        resolve_dns=True,
    )


def validate_url_for_webhook(url: str) -> tuple[bool, str | None]:
    """
    URL validation for webhook destinations.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_url(url, allowed_schemes=["http", "https"], block_private_ips=True, resolve_dns=True)


def validate_url_for_openapi_import(url: str) -> tuple[bool, str | None]:
    """
    URL validation for OpenAPI schema imports.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_url(
        url,
        allowed_schemes=["https"],  # Only HTTPS for schema imports
        block_private_ips=True,
        resolve_dns=True,
    )
