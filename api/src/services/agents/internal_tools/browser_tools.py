"""
Browser automation tools for AI agents using Playwright.
Provides web scraping, screenshot, and browser interaction capabilities.
"""

import base64
import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class BrowserTools:
    """Browser automation tools using Playwright"""

    # Security: Whitelist of allowed domains (configure in settings)
    ALLOWED_DOMAINS: list[str] | None = None  # None = allow public URLs only
    MAX_EXECUTION_TIME = 30  # seconds
    MAX_CONTENT_LENGTH = 50000  # characters

    # SECURITY: Blocked internal IP ranges to prevent SSRF attacks
    BLOCKED_IP_RANGES = [
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
        ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
        ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS metadata)
        ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
        ipaddress.ip_network("0.0.0.0/8"),  # This network
        ipaddress.ip_network("224.0.0.0/4"),  # Multicast
        ipaddress.ip_network("240.0.0.0/4"),  # Reserved
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 private
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    @staticmethod
    def _is_internal_ip(hostname: str) -> bool:
        """
        SECURITY: Check if hostname resolves to an internal/private IP address.
        This prevents SSRF attacks targeting internal services.
        """
        try:
            # Resolve hostname to IP address
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)

            # Check against blocked ranges
            for network in BrowserTools.BLOCKED_IP_RANGES:
                if ip in network:
                    logger.warning(f"SSRF blocked: {hostname} resolves to internal IP {ip_str}")
                    return True

            return False
        except (socket.gaierror, ValueError) as e:
            # If we can't resolve, block it to be safe
            logger.warning(f"SSRF blocked: Could not resolve hostname {hostname}: {e}")
            return True

    @staticmethod
    def _is_url_allowed(url: str) -> bool:
        """Check if URL is allowed (not internal IP and matches allowed domains if set)"""
        try:
            parsed = urlparse(url)

            # SECURITY: Only allow http and https schemes
            if parsed.scheme not in ("http", "https"):
                logger.warning(f"URL scheme not allowed: {parsed.scheme}")
                return False

            hostname = parsed.hostname
            if not hostname:
                logger.warning(f"URL has no hostname: {url}")
                return False

            # SECURITY: Always block internal IPs regardless of ALLOWED_DOMAINS setting
            if BrowserTools._is_internal_ip(hostname):
                return False

            # If specific domains are configured, check against them
            if BrowserTools.ALLOWED_DOMAINS is not None:
                return any(allowed in hostname for allowed in BrowserTools.ALLOWED_DOMAINS)

            # If no specific domains configured, allow public URLs
            return True

        except Exception as e:
            logger.warning(f"URL validation failed for {url}: {e}")
            return False

    @staticmethod
    async def navigate_to_url(url: str, wait_for: str = "domcontentloaded") -> dict[str, Any]:
        """
        Navigate to a URL and extract page content

        Args:
            url: The URL to navigate to
            wait_for: Wait condition (load, domcontentloaded)

        Returns:
            Dict containing title, content, and metadata
        """
        try:
            # Security check
            if not BrowserTools._is_url_allowed(url):
                return {"success": False, "error": f"URL not allowed: {url}", "url": url}

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])

                try:
                    page = await browser.new_page()

                    # Set timeout
                    page.set_default_timeout(BrowserTools.MAX_EXECUTION_TIME * 1000)

                    # Navigate with explicit timeout
                    response = await page.goto(url, wait_until=wait_for, timeout=20000)

                    # Extract content
                    title = await page.title()
                    await page.content()
                    text_content = await page.evaluate("document.body.innerText")

                    # Get meta description
                    meta_description = await page.evaluate("""
                        () => {
                            const meta = document.querySelector('meta[name="description"]');
                            return meta ? meta.content : '';
                        }
                    """)

                    # Limit content length
                    if len(text_content) > BrowserTools.MAX_CONTENT_LENGTH:
                        text_content = text_content[: BrowserTools.MAX_CONTENT_LENGTH] + "..."

                    return {
                        "success": True,
                        "url": url,
                        "title": title,
                        "text_content": text_content,
                        "meta_description": meta_description,
                        "status_code": response.status if response else None,
                        "final_url": page.url,  # In case of redirects
                    }

                finally:
                    await browser.close()

        except PlaywrightTimeout:
            logger.error(f"Timeout navigating to {url}")
            return {"success": False, "error": "Navigation timeout", "url": url}
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            return {"success": False, "error": str(e), "url": url}

    @staticmethod
    async def extract_links(url: str) -> dict[str, Any]:
        """
        Extract all links from a webpage

        Args:
            url: The URL to extract links from

        Returns:
            Dict containing list of links
        """
        try:
            if not BrowserTools._is_url_allowed(url):
                return {"success": False, "error": f"URL not allowed: {url}"}

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                try:
                    page = await browser.new_page()
                    page.set_default_timeout(BrowserTools.MAX_EXECUTION_TIME * 1000)

                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)

                    # Extract all links
                    links = await page.evaluate("""
                        () => {
                            const anchors = Array.from(document.querySelectorAll('a'));
                            return anchors.map(a => ({
                                href: a.href,
                                text: a.textContent.trim(),
                                title: a.title
                            })).filter(link => link.href);
                        }
                    """)

                    return {"success": True, "url": url, "links": links, "count": len(links)}

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
            return {"success": False, "error": str(e), "url": url}

    @staticmethod
    async def extract_structured_data(url: str, selector: str) -> dict[str, Any]:
        """
        Extract structured data from webpage using CSS selector

        Args:
            url: The URL to scrape
            selector: CSS selector for elements to extract

        Returns:
            Dict containing extracted data
        """
        try:
            if not BrowserTools._is_url_allowed(url):
                return {"success": False, "error": f"URL not allowed: {url}"}

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                try:
                    page = await browser.new_page()
                    page.set_default_timeout(BrowserTools.MAX_EXECUTION_TIME * 1000)

                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)

                    # Extract elements using selector
                    elements = await page.query_selector_all(selector)

                    data = []
                    for element in elements:
                        text = await element.inner_text()
                        html = await element.inner_html()
                        data.append({"text": text.strip(), "html": html})

                    return {"success": True, "url": url, "selector": selector, "data": data, "count": len(data)}

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Error extracting data from {url}: {str(e)}")
            return {"success": False, "error": str(e), "url": url}

    @staticmethod
    async def check_element_exists(url: str, selector: str) -> dict[str, Any]:
        """
        Check if an element exists on a webpage

        Args:
            url: The URL to check
            selector: CSS selector to look for

        Returns:
            Dict containing existence status
        """
        try:
            if not BrowserTools._is_url_allowed(url):
                return {"success": False, "error": f"URL not allowed: {url}"}

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                try:
                    page = await browser.new_page()
                    page.set_default_timeout(BrowserTools.MAX_EXECUTION_TIME * 1000)

                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)

                    # Check if element exists
                    element = await page.query_selector(selector)
                    exists = element is not None

                    result = {"success": True, "url": url, "selector": selector, "exists": exists}

                    if exists:
                        text = await element.inner_text()
                        result["text"] = text.strip()

                    return result

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Error checking element on {url}: {str(e)}")
            return {"success": False, "error": str(e), "url": url}


# Tool function wrappers for agent use
async def navigate_to_url(url: str) -> str:
    """Navigate to a URL and extract page content"""
    result = await BrowserTools.navigate_to_url(url)
    if result["success"]:
        return f"Page Title: {result['title']}\n\nContent:\n{result['text_content']}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def extract_links(url: str) -> str:
    """Extract all links from a webpage"""
    result = await BrowserTools.extract_links(url)
    if result["success"]:
        links_text = "\n".join([f"- {link['text']}: {link['href']}" for link in result["links"][:20]])
        return f"Found {result['count']} links:\n{links_text}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def extract_structured_data(url: str, selector: str) -> str:
    """Extract structured data from webpage using CSS selector"""
    result = await BrowserTools.extract_structured_data(url, selector)
    if result["success"]:
        data_text = "\n".join([f"- {item['text']}" for item in result["data"][:10]])
        return f"Found {result['count']} elements matching '{selector}':\n{data_text}"
    return f"Error: {result.get('error', 'Unknown error')}"


async def check_element_exists(url: str, selector: str) -> str:
    """Check if an element exists on a webpage"""
    result = await BrowserTools.check_element_exists(url, selector)
    if result["success"]:
        if result["exists"]:
            return f"Element '{selector}' exists. Text: {result.get('text', 'N/A')}"
        return f"Element '{selector}' does not exist on the page."
    return f"Error: {result.get('error', 'Unknown error')}"
