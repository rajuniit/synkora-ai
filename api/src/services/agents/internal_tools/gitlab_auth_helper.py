"""
GitLab Authentication Helper for Internal Git Tools.

Extracts GitLab OAuth/API tokens from runtime context and injects them into Git URLs.
"""

import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


async def get_gitlab_token_from_context(
    runtime_context: Any, tool_name: str = "gitlab_operations"
) -> tuple[str | None, str | None]:
    """
    Extract GitLab token and base URL from runtime context.

    Args:
        runtime_context: RuntimeContext instance
        tool_name: Name of the tool requesting GitLab access

    Returns:
        Tuple of (token, base_url) or (None, None)
    """
    if not runtime_context:
        logger.debug("No runtime context provided")
        return None, None

    try:
        from src.services.agents.credential_resolver import CredentialResolver

        resolver = CredentialResolver(runtime_context)
        token, base_url = await resolver.get_gitlab_token(tool_name)

        if token:
            logger.info("✅ Successfully retrieved GitLab token from OAuth configuration")

        return token, base_url

    except Exception as e:
        logger.error(f"Failed to get GitLab token: {e}", exc_info=True)
        return None, None


def inject_token_into_url(url: str, token: str) -> str:
    """
    Inject GitLab token into HTTPS URL for authentication.

    Examples:
        'https://gitlab.com/user/repo.git' + token
        -> 'https://oauth2:TOKEN@gitlab.com/user/repo.git'

    Args:
        url: Git repository URL (HTTPS)
        token: GitLab PAT or OAuth token

    Returns:
        URL with injected token
    """
    if not url.startswith("https://"):
        logger.warning(f"URL is not HTTPS, cannot inject token: {url}")
        return url

    if not token:
        logger.warning("No token provided for injection")
        return url

    try:
        parsed = urlparse(url)

        # Check if token already exists in URL
        if "@" in parsed.netloc:
            logger.debug("Token already present in URL")
            return url

        # GitLab uses oauth2:TOKEN format for authentication
        new_netloc = f"oauth2:{token}@{parsed.netloc}"

        new_parsed = parsed._replace(netloc=new_netloc)
        authenticated_url = urlunparse(new_parsed)

        logger.debug(f"Injected token into URL: {parsed.netloc} -> oauth2:TOKEN@{parsed.netloc}")
        return authenticated_url

    except Exception as e:
        logger.error(f"Failed to inject token into URL: {e}")
        return url


async def prepare_authenticated_gitlab_url(
    url: str, runtime_context: Any = None, tool_name: str = "gitlab_operations"
) -> tuple[str, bool]:
    """
    Prepare an authenticated GitLab URL for clone/push/pull operations.

    Args:
        url: Original Git URL (can be HTTPS or SSH)
        runtime_context: RuntimeContext for credential resolution
        tool_name: Tool name for credential lookup

    Returns:
        Tuple of (authenticated_url, used_token)
    """
    # Convert SSH to HTTPS if needed
    if url.startswith("git@"):
        # Convert git@gitlab.com:user/repo.git -> https://gitlab.com/user/repo.git
        url = url.replace(":", "/").replace("git@", "https://")
        logger.debug(f"Converted SSH URL to HTTPS: {url}")

    # Try to get token from context
    token, base_url = await get_gitlab_token_from_context(runtime_context, tool_name)

    if token and url.startswith("https://"):
        authenticated_url = inject_token_into_url(url, token)
        return authenticated_url, True

    logger.warning(
        "⚠️  No GitLab token available - Git operations may fail if SSH keys not configured. "
        "Please configure a GitLab OAuth app or API token for the agent."
    )
    return url, False
