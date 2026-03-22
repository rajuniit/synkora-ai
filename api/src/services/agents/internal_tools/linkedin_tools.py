"""
LinkedIn Tools for professional social media integration.
Uses LinkedIn API with OAuth 2.0 for user authentication.

Configuration stored in OAuthApp:
- provider: "linkedin"
- access_token from OAuth flow or API token

Capabilities:
- Get user profile
- Post text updates
- Post articles
- Share content with URLs
"""

import logging
from typing import Any

import httpx
from sqlalchemy import select

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


async def _get_linkedin_credentials(
    runtime_context: Any, tool_name: str = "internal_linkedin_get_profile"
) -> dict[str, Any]:
    """
    Get LinkedIn API credentials from OAuthApp via runtime context.

    This resolves the token by checking:
    1. User's personal token (user-first resolution)
    2. OAuth app token (fallback)

    Args:
        runtime_context: RuntimeContext with db_session
        tool_name: Name of the tool requesting access

    Returns:
        Dict with access_token

    Raises:
        ValueError: If no token is available
    """
    from src.models.agent_tool import AgentTool
    from src.models.oauth_app import OAuthApp
    from src.models.user_oauth_token import UserOAuthToken
    from src.services.agents.security import decrypt_value

    db = runtime_context.db_session

    # Get agent tool configuration
    result = await db.execute(
        select(AgentTool).filter(
            AgentTool.agent_id == runtime_context.agent_id, AgentTool.tool_name == tool_name, AgentTool.enabled
        )
    )
    agent_tool = result.scalar_one_or_none()

    if not agent_tool or not agent_tool.oauth_app_id:
        raise ValueError(f"No OAuth app configured for tool {tool_name}")

    # Get OAuth app (case-insensitive provider check)
    result = await db.execute(
        select(OAuthApp).filter(
            OAuthApp.id == agent_tool.oauth_app_id, OAuthApp.provider.ilike("linkedin"), OAuthApp.is_active
        )
    )
    oauth_app = result.scalar_one_or_none()

    if not oauth_app:
        raise ValueError("No active LinkedIn OAuth app found")

    credentials = {}

    # Try user token first (user-first resolution)
    result = await db.execute(select(UserOAuthToken).filter(UserOAuthToken.oauth_app_id == oauth_app.id))
    user_token = result.scalar_one_or_none()

    if user_token and user_token.access_token:
        credentials["access_token"] = decrypt_value(user_token.access_token)
        logger.info(f"✅ Using user's LinkedIn token (OAuth app: '{oauth_app.app_name}')")
    elif oauth_app.access_token:
        # Fall back to OAuth app token
        credentials["access_token"] = decrypt_value(oauth_app.access_token)
        logger.info(f"✅ Using LinkedIn OAuth app token '{oauth_app.app_name}'")
    elif oauth_app.api_token:
        # Fall back to API token
        credentials["access_token"] = decrypt_value(oauth_app.api_token)
        logger.info(f"✅ Using LinkedIn API token '{oauth_app.app_name}'")

    if not credentials.get("access_token"):
        raise ValueError("No LinkedIn access token available. Please connect LinkedIn.")

    return credentials


async def _make_linkedin_request(
    endpoint: str,
    method: str = "GET",
    credentials: dict[str, Any] = None,
    params: dict[str, Any] = None,
    json_data: dict[str, Any] = None,
    headers: dict[str, str] = None,
) -> dict[str, Any]:
    """Make authenticated request to LinkedIn API."""
    default_headers = {
        "Authorization": f"Bearer {credentials.get('access_token')}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    if headers:
        default_headers.update(headers)

    url = f"{LINKEDIN_API_BASE}{endpoint}"

    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=default_headers, params=params, timeout=30.0)
        elif method == "POST":
            response = await client.post(url, headers=default_headers, json=json_data, timeout=30.0)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 401:
            raise ValueError("LinkedIn authentication failed. Token may be expired.")
        elif response.status_code == 403:
            raise ValueError("LinkedIn API access forbidden. Check your app permissions.")
        elif response.status_code == 429:
            raise ValueError("LinkedIn API rate limit exceeded. Please try again later.")

        response.raise_for_status()

        # Handle empty responses (201 Created, 204 No Content)
        if response.status_code in (201, 204) or not response.content:
            # For 201 Created, extract ID from headers
            result = {"success": True}
            if "x-restli-id" in response.headers:
                result["id"] = response.headers["x-restli-id"]
            if "location" in response.headers:
                result["location"] = response.headers["location"]
            return result

        return response.json()


async def internal_linkedin_get_profile(
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the authenticated user's LinkedIn profile.

    Returns:
        User profile information
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        # Get basic profile using OpenID Connect userinfo endpoint
        result = await _make_linkedin_request(
            "/userinfo",
            credentials=credentials,
        )

        return {
            "success": True,
            "profile": {
                "id": result.get("sub"),
                "name": result.get("name"),
                "given_name": result.get("given_name"),
                "family_name": result.get("family_name"),
                "picture": result.get("picture"),
                "email": result.get("email"),
                "email_verified": result.get("email_verified"),
                "locale": result.get("locale"),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get LinkedIn profile: {e}")
        return {"success": False, "error": str(e)}


async def internal_linkedin_post_text(
    text: str,
    visibility: str = "PUBLIC",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Post a text update to LinkedIn.

    Args:
        text: Post content (max 3000 characters)
        visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN" (default: PUBLIC)

    Returns:
        Created post details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not text:
        return {"success": False, "error": "Post text is required"}

    if len(text) > 3000:
        return {"success": False, "error": f"Post exceeds 3000 characters ({len(text)} chars)"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        # First get the user's profile to get their URN
        profile_result = await internal_linkedin_get_profile(
            config=config,
            runtime_context=runtime_context,
        )

        if not profile_result.get("success"):
            return profile_result

        user_id = profile_result.get("profile", {}).get("id")
        if not user_id:
            return {"success": False, "error": "Failed to get user ID"}

        author_urn = f"urn:li:person:{user_id}"

        # Create post using Posts API
        json_data = {
            "author": author_urn,
            "commentary": text,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        result = await _make_linkedin_request(
            "/posts",
            method="POST",
            credentials=credentials,
            json_data=json_data,
        )

        # Extract post ID from response header or body
        post_id = result.get("id") or result.get("x-restli-id")

        return {
            "success": True,
            "post": {
                "id": post_id,
                "text": text,
                "visibility": visibility,
                "author": author_urn,
            },
            "message": "Post published successfully",
        }

    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}")
        return {"success": False, "error": str(e)}


async def internal_linkedin_share_url(
    url: str,
    text: str | None = None,
    title: str | None = None,
    description: str | None = None,
    visibility: str = "PUBLIC",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Share a URL/article on LinkedIn.

    Args:
        url: URL to share
        text: Commentary text (optional)
        title: Title override for the shared content (optional)
        description: Description override (optional)
        visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN" (default: PUBLIC)

    Returns:
        Created share details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not url:
        return {"success": False, "error": "URL is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        # Get user profile for author URN
        profile_result = await internal_linkedin_get_profile(
            config=config,
            runtime_context=runtime_context,
        )

        if not profile_result.get("success"):
            return profile_result

        user_id = profile_result.get("profile", {}).get("id")
        if not user_id:
            return {"success": False, "error": "Failed to get user ID"}

        author_urn = f"urn:li:person:{user_id}"

        # Create share with article content
        json_data = {
            "author": author_urn,
            "commentary": text or "",
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": url,
                    "title": title,
                    "description": description,
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        # Remove None values from article
        json_data["content"]["article"] = {k: v for k, v in json_data["content"]["article"].items() if v is not None}

        result = await _make_linkedin_request(
            "/posts",
            method="POST",
            credentials=credentials,
            json_data=json_data,
        )

        post_id = result.get("id") or result.get("x-restli-id")

        return {
            "success": True,
            "share": {
                "id": post_id,
                "url": url,
                "text": text,
                "visibility": visibility,
            },
            "message": "URL shared successfully",
        }

    except Exception as e:
        logger.error(f"Failed to share on LinkedIn: {e}")
        return {"success": False, "error": str(e)}


async def internal_linkedin_get_company_info(
    company_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get information about a LinkedIn company/organization.

    Args:
        company_id: LinkedIn company/organization ID

    Returns:
        Company information
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not company_id:
        return {"success": False, "error": "Company ID is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        result = await _make_linkedin_request(
            f"/organizations/{company_id}",
            credentials=credentials,
        )

        return {
            "success": True,
            "company": {
                "id": result.get("id"),
                "name": result.get("localizedName"),
                "description": result.get("localizedDescription"),
                "website": result.get("websiteUrl"),
                "industry": result.get("localizedSpecialties"),
                "logo": result.get("logoV2", {}).get("original"),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get LinkedIn company info: {e}")
        return {"success": False, "error": str(e)}


async def internal_linkedin_get_posts(
    count: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the authenticated user's LinkedIn posts/activity.

    NOTE: This feature requires LinkedIn Marketing API access with 'r_member_social' scope,
    which is a restricted permission requiring LinkedIn partner approval.
    Standard LinkedIn apps can post content but cannot read post history.

    Args:
        count: Number of posts to retrieve (max 100, default 10)

    Returns:
        List of user's recent posts
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    # Limit count to reasonable range
    count = min(max(1, count), 100)

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        # Get user profile for author URN
        profile_result = await internal_linkedin_get_profile(
            config=config,
            runtime_context=runtime_context,
        )

        if not profile_result.get("success"):
            return profile_result

        user_id = profile_result.get("profile", {}).get("id")
        if not user_id:
            return {"success": False, "error": "Failed to get user ID"}

        author_urn = f"urn:li:person:{user_id}"

        # Get posts using the Posts API with author filter
        # Note: This requires 'r_member_social' scope (Marketing API)
        result = await _make_linkedin_request(
            "/posts",
            credentials=credentials,
            params={
                "author": author_urn,
                "q": "author",
                "count": count,
            },
        )

        posts = []
        elements = result.get("elements", [])

        for post in elements:
            post_data = {
                "id": post.get("id"),
                "text": post.get("commentary"),
                "visibility": post.get("visibility"),
                "created_at": post.get("createdAt"),
                "last_modified": post.get("lastModifiedAt"),
                "lifecycle_state": post.get("lifecycleState"),
            }

            # Extract content info if present
            content = post.get("content", {})
            if content:
                if "article" in content:
                    post_data["article"] = {
                        "url": content["article"].get("source"),
                        "title": content["article"].get("title"),
                        "description": content["article"].get("description"),
                    }
                elif "media" in content:
                    post_data["media"] = content["media"]

            posts.append(post_data)

        return {
            "success": True,
            "posts": posts,
            "count": len(posts),
            "profile_id": user_id,
        }

    except ValueError as e:
        error_msg = str(e)
        # Provide more helpful error for permission issues
        if "forbidden" in error_msg.lower() or "403" in error_msg:
            logger.error(f"Failed to get LinkedIn posts: {e}")
            return {
                "success": False,
                "error": "Reading LinkedIn posts requires the 'r_member_social' scope, "
                "which is only available through LinkedIn's Marketing API partner program. "
                "Standard LinkedIn apps can post content but cannot read post history.",
            }
        return {"success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Failed to get LinkedIn posts: {e}")
        return {"success": False, "error": str(e)}


async def internal_linkedin_post_with_image(
    text: str,
    image_url: str,
    visibility: str = "PUBLIC",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Post text with an image to LinkedIn.

    Args:
        text: Post content
        image_url: URL of the image to include
        visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN"

    Returns:
        Created post details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not text:
        return {"success": False, "error": "Post text is required"}

    if not image_url:
        return {"success": False, "error": "Image URL is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_linkedin_get_profile")
        credentials = await _get_linkedin_credentials(runtime_context, tool_name)

        # Get user profile for author URN
        profile_result = await internal_linkedin_get_profile(
            config=config,
            runtime_context=runtime_context,
        )

        if not profile_result.get("success"):
            return profile_result

        user_id = profile_result.get("profile", {}).get("id")
        if not user_id:
            return {"success": False, "error": "Failed to get user ID"}

        author_urn = f"urn:li:person:{user_id}"

        # Create post with image
        # Note: For proper image upload, you'd need to use the Assets API
        # This simplified version uses an external image URL
        json_data = {
            "author": author_urn,
            "commentary": text,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {
                "article": {
                    "source": image_url,
                    "title": "",
                    "description": "",
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        result = await _make_linkedin_request(
            "/posts",
            method="POST",
            credentials=credentials,
            json_data=json_data,
        )

        post_id = result.get("id") or result.get("x-restli-id")

        return {
            "success": True,
            "post": {
                "id": post_id,
                "text": text,
                "image_url": image_url,
                "visibility": visibility,
            },
            "message": "Post with image published successfully",
        }

    except Exception as e:
        logger.error(f"Failed to post image to LinkedIn: {e}")
        return {"success": False, "error": str(e)}
