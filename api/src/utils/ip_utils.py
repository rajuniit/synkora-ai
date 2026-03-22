"""
Shared client-IP extraction utility.

Both the security middleware and the rate-limit middleware need to resolve
the real client IP from behind a reverse proxy. Having one canonical
implementation keeps the trust logic consistent and avoids the previous
bug where the two copies used different strategies (leftmost vs rightmost).

Strategy — rightmost non-trusted IP:
  X-Forwarded-For is appended to by each hop:  client, proxy1, proxy2, …
  A malicious client can prepend fake IPs, so the *leftmost* entry is not
  reliable.  Walking from the right and stopping at the first IP that is
  not on our trusted-proxy allowlist gives us the true origin even if the
  attacker forged earlier entries.
"""

import ipaddress
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Trusted proxy allowlist
# ---------------------------------------------------------------------------

# Standard RFC-1918 private ranges plus loopback — shared by both middlewares.
TRUSTED_PROXY_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("127.0.0.0/8"),    # IPv4 loopback
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("10.0.0.0/8"),      # RFC-1918 class A
    ipaddress.ip_network("172.16.0.0/12"),   # RFC-1918 class B
    ipaddress.ip_network("192.168.0.0/16"),  # RFC-1918 class C
    ipaddress.ip_network("169.254.0.0/16"),  # IPv4 link-local
    ipaddress.ip_network("172.17.0.0/16"),   # Docker default bridge
    ipaddress.ip_network("fc00::/7"),        # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
]

# Operators can extend the allowlist via environment variable.
# Format: comma-separated CIDR notation, e.g. "10.0.0.0/8,192.168.1.0/24"
_extra = os.getenv("TRUSTED_PROXIES", "")
if _extra:
    for _cidr in _extra.split(","):
        _cidr = _cidr.strip()
        if _cidr:
            try:
                TRUSTED_PROXY_NETWORKS.append(ipaddress.ip_network(_cidr))
            except ValueError as _e:
                logger.warning(f"Invalid TRUSTED_PROXIES entry '{_cidr}': {_e}")


def is_trusted_proxy(ip_str: str) -> bool:
    """Return True if *ip_str* belongs to a trusted proxy network."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in TRUSTED_PROXY_NETWORKS)
    except ValueError:
        return False


def get_client_ip(direct_ip: str, forwarded_for: str | None, real_ip: str | None = None) -> str:
    """
    Resolve the real client IP address.

    Uses the *rightmost non-trusted* entry from X-Forwarded-For so that
    clients cannot spoof their IP by prepending fake addresses to the header.

    Args:
        direct_ip:     The IP of the TCP peer (``request.client.host``).
        forwarded_for: Value of the ``X-Forwarded-For`` header, or None.
        real_ip:       Value of the ``X-Real-IP`` header, or None.

    Returns:
        Best-effort real client IP string.
    """
    if direct_ip == "unknown" or not is_trusted_proxy(direct_ip):
        # Direct connection — no need to look at forwarded headers.
        return direct_ip

    # Direct peer is a trusted proxy; inspect forwarded headers.
    if forwarded_for:
        chain = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        # Walk from right to left; stop at the first non-trusted entry.
        for ip in reversed(chain):
            try:
                ipaddress.ip_address(ip)  # validate format
                if not is_trusted_proxy(ip):
                    return ip
            except ValueError:
                continue
        # All entries are trusted proxies — fall back to the leftmost (client).
        if chain:
            return chain[0]

    if real_ip and real_ip.strip():
        candidate = real_ip.strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            logger.warning(f"Invalid IP in X-Real-IP: {candidate}")

    return direct_ip
