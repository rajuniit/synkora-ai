"""
Input Sanitizer for User-Provided Content

SECURITY: Sanitizes user input to prevent XSS (Cross-Site Scripting) attacks.
This provides defense-in-depth by stripping dangerous HTML before storage,
in addition to proper output escaping on the frontend.
"""

import html
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Dangerous HTML tags that can execute scripts or embed content
DANGEROUS_TAGS = [
    "script",
    "iframe",
    "object",
    "embed",
    "applet",
    "link",
    "meta",
    "base",
    "form",
    "input",
    "button",
    "select",
    "textarea",
]

# Dangerous HTML attributes that can execute JavaScript
DANGEROUS_ATTRS = [
    "onclick",
    "ondblclick",
    "onmousedown",
    "onmouseup",
    "onmouseover",
    "onmousemove",
    "onmouseout",
    "onkeypress",
    "onkeydown",
    "onkeyup",
    "onload",
    "onerror",
    "onsubmit",
    "onreset",
    "onselect",
    "onblur",
    "onfocus",
    "onchange",
    "onabort",
    "oncancel",
    "oncanplay",
    "onclose",
    "oncontextmenu",
    "oncopy",
    "oncut",
    "ondrag",
    "ondragend",
    "ondragenter",
    "ondragleave",
    "ondragover",
    "ondragstart",
    "ondrop",
    "oninput",
    "oninvalid",
    "onpaste",
    "onscroll",
    "onwheel",
    "formaction",
    "xlink:href",
]

# Pattern for dangerous protocol schemes in href/src
DANGEROUS_PROTOCOLS = re.compile(r"^\s*(?:javascript|vbscript|data|blob):", re.IGNORECASE)


def sanitize_html_string(content: str) -> str:
    """
    Sanitize a string by removing dangerous HTML.

    SECURITY: Strips dangerous tags, attributes, and protocol handlers
    while preserving safe content.

    Args:
        content: String content that may contain HTML

    Returns:
        Sanitized string with dangerous HTML removed
    """
    if not content or not isinstance(content, str):
        return content

    sanitized = content

    # Remove dangerous tags and their content
    for tag in DANGEROUS_TAGS:
        # Remove tags with content: <script>...</script>
        sanitized = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>",
            "",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        # Remove self-closing tags: <script />
        sanitized = re.sub(
            rf"<{tag}[^>]*/?>",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

    # Remove dangerous attributes from remaining tags
    for attr in DANGEROUS_ATTRS:
        # Match attr="value" or attr='value' or attr=value
        sanitized = re.sub(
            rf'\s+{attr}\s*=\s*["\'][^"\']*["\']',
            "",
            sanitized,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            rf"\s+{attr}\s*=\s*[^\s>]+",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

    # Remove javascript: and other dangerous protocols from href/src
    sanitized = re.sub(
        r'(href|src)\s*=\s*["\']?\s*(?:javascript|vbscript|data|blob):[^"\'>\s]*["\']?',
        "",
        sanitized,
        flags=re.IGNORECASE,
    )

    return sanitized


def sanitize_dict_values(data: dict[str, Any], keys_to_sanitize: list[str] | None = None) -> dict[str, Any]:
    """
    Recursively sanitize string values in a dictionary.

    Args:
        data: Dictionary containing user-provided data
        keys_to_sanitize: Optional list of specific keys to sanitize.
                         If None, sanitizes all string values.

    Returns:
        Dictionary with sanitized string values
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Sanitize if no specific keys listed, or if this key should be sanitized
            if keys_to_sanitize is None or key in keys_to_sanitize:
                result[key] = sanitize_html_string(value)
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = sanitize_dict_values(value, keys_to_sanitize)
        elif isinstance(value, list):
            result[key] = sanitize_list_values(value, keys_to_sanitize)
        else:
            result[key] = value

    return result


def sanitize_list_values(data: list[Any], keys_to_sanitize: list[str] | None = None) -> list[Any]:
    """
    Recursively sanitize values in a list.

    Args:
        data: List containing user-provided data
        keys_to_sanitize: Optional list of specific keys to sanitize in nested dicts

    Returns:
        List with sanitized values
    """
    if not isinstance(data, list):
        return data

    result = []
    for item in data:
        if isinstance(item, str):
            result.append(sanitize_html_string(item))
        elif isinstance(item, dict):
            result.append(sanitize_dict_values(item, keys_to_sanitize))
        elif isinstance(item, list):
            result.append(sanitize_list_values(item, keys_to_sanitize))
        else:
            result.append(item)

    return result


def sanitize_suggestion_prompts(prompts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """
    Sanitize suggestion prompts to prevent XSS.

    SECURITY: Specifically sanitizes user-visible fields in suggestion prompts
    like title, description, and prompt content.

    Args:
        prompts: List of suggestion prompt dictionaries

    Returns:
        Sanitized list of suggestion prompts
    """
    if not prompts:
        return []

    # Fields that may contain user-visible text and need sanitization
    fields_to_sanitize = ["title", "description", "prompt", "icon", "label", "text", "content"]

    return sanitize_list_values(prompts, fields_to_sanitize)


def html_escape_string(content: str) -> str:
    """
    Escape HTML entities in a string.

    Use this for content that needs to preserve text but prevent HTML interpretation.

    Args:
        content: String to escape

    Returns:
        HTML-escaped string
    """
    if not content or not isinstance(content, str):
        return content

    return html.escape(content, quote=True)
