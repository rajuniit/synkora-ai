"""
Browser automation tools — proxied to the synkora-scraper microservice.

All Playwright/crawl4ai calls are forwarded to the scraper service so that
the API image no longer needs those packages installed.
"""

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


class BrowserTools:
    """Browser automation tools — delegated to the scraper microservice."""

    ALLOWED_DOMAINS: list[str] | None = None
    MAX_EXECUTION_TIME = 30
    MAX_CONTENT_LENGTH = 50000

    @staticmethod
    def _is_internal_ip(hostname: str) -> bool:
        """Return True if *hostname* resolves to a private/internal IP (SSRF guard)."""
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            return any(ip in net for net in _BLOCKED_IP_NETWORKS)
        except Exception:
            return True  # treat unresolvable as blocked

    @staticmethod
    def _is_url_allowed(url: str) -> bool:
        """Return True if *url* passes SSRF checks and domain allow-list."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname or ""
            if BrowserTools._is_internal_ip(hostname):
                return False
            if BrowserTools.ALLOWED_DOMAINS:
                return any(hostname == d or hostname.endswith("." + d) for d in BrowserTools.ALLOWED_DOMAINS)
            return True
        except Exception:
            return False

    @staticmethod
    async def navigate_to_url(url: str, wait_for: str = "domcontentloaded") -> dict[str, Any]:
        if not BrowserTools._is_url_allowed(url):
            return {"success": False, "error": f"URL not allowed: {url}"}
        from src.core.scraper_client import get_scraper_client

        return await get_scraper_client().browser_simple_navigate(url=url, wait_for=wait_for)

    @staticmethod
    async def extract_links(url: str) -> dict[str, Any]:
        if not BrowserTools._is_url_allowed(url):
            return {"success": False, "error": f"URL not allowed: {url}"}
        from src.core.scraper_client import get_scraper_client

        return await get_scraper_client().browser_extract_links(url=url)

    @staticmethod
    async def extract_structured_data(url: str, selector: str) -> dict[str, Any]:
        if not BrowserTools._is_url_allowed(url):
            return {"success": False, "error": f"URL not allowed: {url}"}
        from src.core.scraper_client import get_scraper_client

        return await get_scraper_client().browser_extract_structured_data(url=url, selector=selector)

    @staticmethod
    async def check_element_exists(url: str, selector: str) -> dict[str, Any]:
        if not BrowserTools._is_url_allowed(url):
            return {"success": False, "error": f"URL not allowed: {url}"}
        from src.core.scraper_client import get_scraper_client

        return await get_scraper_client().browser_check_element_exists(url=url, selector=selector)


# ---------------------------------------------------------------------------
# Tool function wrappers for agent use
# ---------------------------------------------------------------------------


async def navigate_to_url(url: str) -> str:
    """Navigate to a URL and extract page content"""
    result = await BrowserTools.navigate_to_url(url)
    if result.get("success"):
        return f"Page Title: {result.get('title', '')}\n\nContent:\n{result.get('text_content', '')}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def extract_links(url: str) -> str:
    """Extract all links from a webpage"""
    result = await BrowserTools.extract_links(url)
    if result.get("success"):
        links = result.get("links", [])
        links_text = "\n".join([f"- {link.get('text', '')}: {link.get('href', '')}" for link in links[:20]])
        return f"Found {result.get('count', 0)} links:\n{links_text}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def extract_structured_data(url: str, selector: str) -> str:
    """Extract structured data from webpage using CSS selector"""
    result = await BrowserTools.extract_structured_data(url, selector)
    if result.get("success"):
        data = result.get("data", [])
        data_text = "\n".join([f"- {item.get('text', '')}" for item in data[:10]])
        return f"Found {result.get('count', 0)} elements matching '{selector}':\n{data_text}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def check_element_exists(url: str, selector: str) -> str:
    """Check if an element exists on a webpage"""
    result = await BrowserTools.check_element_exists(url, selector)
    if result.get("success"):
        if result.get("exists"):
            return f"Element '{selector}' exists. Text: {result.get('text', 'N/A')}"
        return f"Element '{selector}' does not exist on the page."
    return f"Error: {result.get('error', 'Unknown error')}"
