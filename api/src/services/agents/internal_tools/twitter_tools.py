"""
Twitter/X Tools for social media integration.
Uses Twitter API v2 with OAuth 2.0 for user authentication.

Configuration stored in OAuthApp:
- provider: "twitter"
- api_token (Bearer Token) for read operations
- OAuth credentials for write operations

Capabilities:
- Read user timeline
- Read bookmarks
- Post tweets
- Search tweets
- Get user info
"""

import logging
from typing import Any

import httpx
from sqlalchemy import select

logger = logging.getLogger(__name__)

TWITTER_API_BASE = "https://api.twitter.com/2"


async def _get_twitter_credentials(
    runtime_context: Any, tool_name: str = "internal_twitter_get_my_profile"
) -> dict[str, Any]:
    """
    Get Twitter API credentials from OAuthApp via runtime context.

    This resolves the token by checking:
    1. User's personal token (user-first resolution)
    2. OAuth app token (fallback)

    Args:
        runtime_context: RuntimeContext with db_session
        tool_name: Name of the tool requesting access

    Returns:
        Dict with bearer_token or access_token

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
            OAuthApp.id == agent_tool.oauth_app_id, OAuthApp.provider.ilike("twitter"), OAuthApp.is_active
        )
    )
    oauth_app = result.scalar_one_or_none()

    if not oauth_app:
        raise ValueError("No active Twitter OAuth app found")

    credentials = {}

    # Try user token first (user-first resolution)
    result = await db.execute(select(UserOAuthToken).filter(UserOAuthToken.oauth_app_id == oauth_app.id))
    user_token = result.scalar_one_or_none()

    if user_token and user_token.access_token:
        from datetime import UTC, datetime

        user_token_expired = user_token.token_expires_at is not None and user_token.token_expires_at.replace(
            tzinfo=UTC
        ) < datetime.now(UTC)
        if user_token_expired and user_token.refresh_token:
            try:
                from src.services.oauth.twitter_oauth import TwitterOAuth

                client_secret = decrypt_value(oauth_app.client_secret)
                tw_oauth = TwitterOAuth(
                    client_id=oauth_app.client_id,
                    client_secret=client_secret,
                    redirect_uri=oauth_app.redirect_uri,
                )
                refreshed = await tw_oauth.refresh_access_token(decrypt_value(user_token.refresh_token))
                new_access = refreshed.get("access_token")
                new_refresh = refreshed.get("refresh_token")
                new_expires_in = refreshed.get("expires_in")
                if new_access:
                    from datetime import timedelta

                    from src.services.agents.security import encrypt_value as _enc

                    user_token.access_token = _enc(new_access)
                    if new_refresh:
                        user_token.refresh_token = _enc(new_refresh)
                    if new_expires_in:
                        user_token.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(new_expires_in))
                    await db.commit()
                    logger.info(f"✅ Refreshed user Twitter token (OAuth app: '{oauth_app.app_name}')")
                    credentials["access_token"] = new_access
                    credentials["bearer_token"] = new_access
                    credentials["token_type"] = "user"
            except Exception as refresh_err:
                logger.warning(f"User Twitter token refresh failed: {refresh_err} — using stored token")
                decrypted_token = decrypt_value(user_token.access_token)
                credentials["access_token"] = decrypted_token
                credentials["bearer_token"] = decrypted_token
                credentials["token_type"] = "user"
        else:
            decrypted_token = decrypt_value(user_token.access_token)
            credentials["access_token"] = decrypted_token
            credentials["bearer_token"] = decrypted_token  # Use same token for both
            credentials["token_type"] = "user"  # OAuth 2.0 user context — can read AND write
        logger.info(f"✅ Using user's Twitter token (OAuth app: '{oauth_app.app_name}')")
    elif oauth_app.access_token:
        # Fall back to OAuth app access token (user context)
        # Try to refresh if expired and refresh_token is available
        from datetime import UTC, datetime

        token_expired = oauth_app.token_expires_at is not None and oauth_app.token_expires_at.replace(
            tzinfo=UTC
        ) < datetime.now(UTC)
        if token_expired and oauth_app.refresh_token:
            try:
                from src.services.oauth.twitter_oauth import TwitterOAuth

                client_secret = decrypt_value(oauth_app.client_secret)
                tw_oauth = TwitterOAuth(
                    client_id=oauth_app.client_id,
                    client_secret=client_secret,
                    redirect_uri=oauth_app.redirect_uri,
                )
                refreshed = await tw_oauth.refresh_access_token(decrypt_value(oauth_app.refresh_token))
                new_access = refreshed.get("access_token")
                new_refresh = refreshed.get("refresh_token")
                new_expires_in = refreshed.get("expires_in")
                if new_access:
                    from src.services.agents.security import encrypt_value as _enc

                    oauth_app.access_token = _enc(new_access)
                    if new_refresh:
                        oauth_app.refresh_token = _enc(new_refresh)
                    if new_expires_in:
                        from datetime import timedelta

                        oauth_app.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(new_expires_in))
                    await db.commit()
                    logger.info(f"✅ Refreshed Twitter token for app '{oauth_app.app_name}'")
                    credentials["access_token"] = new_access
                    credentials["bearer_token"] = new_access
                    credentials["token_type"] = "user"
            except Exception as refresh_err:
                logger.warning(f"Twitter token refresh failed: {refresh_err} — falling back to stored token")
                credentials["access_token"] = decrypt_value(oauth_app.access_token)
                credentials["bearer_token"] = credentials["access_token"]
                credentials["token_type"] = "user"
        else:
            credentials["access_token"] = decrypt_value(oauth_app.access_token)
            credentials["bearer_token"] = credentials["access_token"]
            credentials["token_type"] = "user"
        logger.info(f"✅ Using Twitter OAuth app token '{oauth_app.app_name}'")
    elif oauth_app.api_token:
        # App-only Bearer Token — READ ONLY. Cannot post tweets or access user-context endpoints.
        credentials["bearer_token"] = decrypt_value(oauth_app.api_token)
        credentials["token_type"] = "app_only"
        logger.info(f"✅ Using Twitter API token '{oauth_app.app_name}' (app-only, read-only)")

    if not credentials.get("bearer_token") and not credentials.get("access_token"):
        raise ValueError("No Twitter access token available. Please connect Twitter.")

    return credentials


async def _make_twitter_request(
    endpoint: str,
    method: str = "GET",
    credentials: dict[str, Any] = None,
    params: dict[str, Any] = None,
    json_data: dict[str, Any] = None,
) -> dict[str, Any]:
    """Make authenticated request to Twitter API."""
    headers = {
        "Authorization": f"Bearer {credentials.get('bearer_token')}",
        "Content-Type": "application/json",
    }

    url = f"{TWITTER_API_BASE}{endpoint}"

    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=json_data, timeout=30.0)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers, timeout=30.0)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 401:
            raise ValueError("Twitter authentication failed. Check your API credentials.")
        elif response.status_code == 403:
            is_write = method in ("POST", "DELETE")
            token_type = (credentials or {}).get("token_type", "unknown")
            if is_write and token_type == "app_only":
                raise ValueError(
                    "Cannot post tweets with an app-only Bearer Token. "
                    "Twitter requires OAuth 2.0 user authentication (tweet.write scope) for write operations. "
                    "Go to My Connections → Twitter → reconnect via OAuth flow instead of pasting an API token."
                )
            # Try to extract Twitter's error detail from the response body
            try:
                error_body = response.json()
                detail = error_body.get("detail") or error_body.get("title") or ""
            except Exception:
                error_body = {}
                detail = ""
            logger.error(f"Twitter 403 response body: {error_body}")
            if is_write:
                raise ValueError(
                    "Twitter returned 403 on a write operation. Your stored token likely lacks tweet.write scope. "
                    "To fix: go to My Connections → Twitter → Disconnect, then reconnect via OAuth to get a fresh token. "
                    "Also ensure your Twitter app has 'Read and Write' permissions enabled in the Developer Portal "
                    "(Settings → User authentication settings → App permissions → Read and Write)."
                )
            if "453" in response.text or "authorization" in response.text.lower():
                raise ValueError(
                    "Twitter returned 403: your app needs 'Read and Write' permissions enabled in the "
                    "Twitter Developer Portal, and your access token must be regenerated after changing permissions."
                )
            raise ValueError(
                f"Twitter API access forbidden (403). {detail} "
                "Ensure your Twitter app has 'Read and Write' permissions and your token has tweet.write scope."
            )
        elif response.status_code == 429:
            raise ValueError("Twitter API rate limit exceeded. Please try again later.")

        response.raise_for_status()
        return response.json()


async def internal_twitter_get_user_timeline(
    user_id: str | None = None,
    username: str | None = None,
    max_results: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get tweets from a user's timeline.

    Args:
        user_id: Twitter user ID (optional if username provided)
        username: Twitter username/handle (optional if user_id provided)
        max_results: Maximum number of tweets to return (default 10, max 100)

    Returns:
        List of tweets with metadata
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        # Get user ID if username provided
        if username and not user_id:
            user_result = await internal_twitter_get_user_by_username(
                username=username,
                config=config,
                runtime_context=runtime_context,
            )
            if not user_result.get("success"):
                return user_result
            user_id = user_result.get("user", {}).get("id")

        if not user_id:
            return {"success": False, "error": "Either user_id or username is required"}

        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
            "expansions": "author_id,referenced_tweets.id",
            "user.fields": "name,username,profile_image_url",
        }

        result = await _make_twitter_request(
            f"/users/{user_id}/tweets",
            credentials=credentials,
            params=params,
        )

        tweets = []
        for tweet in result.get("data", []):
            tweets.append(
                {
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {}),
                    "author_id": tweet.get("author_id"),
                }
            )

        return {
            "success": True,
            "user_id": user_id,
            "tweets": tweets,
            "count": len(tweets),
        }

    except Exception as e:
        logger.error(f"Failed to get Twitter timeline: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_get_bookmarks(
    max_results: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get authenticated user's bookmarked tweets.
    Requires OAuth 2.0 User Context with bookmark.read scope.

    Args:
        max_results: Maximum number of bookmarks to return (default 10, max 100)

    Returns:
        List of bookmarked tweets
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        # First get the authenticated user's ID
        me_result = await _make_twitter_request("/users/me", credentials=credentials)
        user_id = me_result.get("data", {}).get("id")

        if not user_id:
            return {"success": False, "error": "Failed to get authenticated user"}

        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id,context_annotations",
            "expansions": "author_id",
            "user.fields": "name,username,profile_image_url",
        }

        result = await _make_twitter_request(
            f"/users/{user_id}/bookmarks",
            credentials=credentials,
            params=params,
        )

        bookmarks = []
        users_map = {}

        # Build users map from includes
        for user in result.get("includes", {}).get("users", []):
            users_map[user["id"]] = {
                "name": user.get("name"),
                "username": user.get("username"),
            }

        for tweet in result.get("data", []):
            author = users_map.get(tweet.get("author_id"), {})
            bookmarks.append(
                {
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {}),
                    "author": author,
                }
            )

        return {
            "success": True,
            "bookmarks": bookmarks,
            "count": len(bookmarks),
        }

    except Exception as e:
        logger.error(f"Failed to get Twitter bookmarks: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_post_tweet(
    text: str,
    reply_to_tweet_id: str | None = None,
    quote_tweet_id: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Post a new tweet.
    Requires OAuth 2.0 User Context with tweet.write scope.

    Args:
        text: Tweet text (max 280 characters)
        reply_to_tweet_id: ID of tweet to reply to (optional)
        quote_tweet_id: ID of tweet to quote (optional)

    Returns:
        Created tweet details
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not text:
        return {"success": False, "error": "Tweet text is required"}

    if len(text) > 280:
        return {"success": False, "error": f"Tweet exceeds 280 characters ({len(text)} chars)"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        # Posting requires OAuth 2.0 user context — app-only bearer tokens always 403 on writes
        if credentials.get("token_type") == "app_only":
            return {
                "success": False,
                "error": (
                    "Posting tweets requires OAuth 2.0 user authentication with tweet.write scope. "
                    "Your current configuration only has an app-only Bearer Token (api_token), which is read-only. "
                    "To fix: go to My Connections → Twitter → reconnect via the OAuth flow (not by pasting an API token). "
                    "Also ensure your Twitter app has 'Read and Write' permissions in the Developer Portal "
                    "and that you regenerated your access tokens after changing the permissions."
                ),
            }

        json_data = {"text": text}

        if reply_to_tweet_id:
            json_data["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}

        if quote_tweet_id:
            json_data["quote_tweet_id"] = quote_tweet_id

        result = await _make_twitter_request(
            "/tweets",
            method="POST",
            credentials=credentials,
            json_data=json_data,
        )

        tweet_data = result.get("data", {})

        return {
            "success": True,
            "tweet": {
                "id": tweet_data.get("id"),
                "text": tweet_data.get("text"),
            },
            "url": f"https://twitter.com/i/web/status/{tweet_data.get('id')}",
        }

    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_search_tweets(
    query: str,
    max_results: int = 10,
    sort_order: str = "relevancy",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Search for tweets matching a query.

    Args:
        query: Search query (supports Twitter search operators)
        max_results: Maximum results (default 10, max 100)
        sort_order: "relevancy" or "recency"

    Returns:
        List of matching tweets
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not query:
        return {"success": False, "error": "Search query is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "sort_order": sort_order,
            "tweet.fields": "created_at,public_metrics,author_id,context_annotations",
            "expansions": "author_id",
            "user.fields": "name,username,profile_image_url",
        }

        result = await _make_twitter_request(
            "/tweets/search/recent",
            credentials=credentials,
            params=params,
        )

        tweets = []
        users_map = {}

        for user in result.get("includes", {}).get("users", []):
            users_map[user["id"]] = {
                "name": user.get("name"),
                "username": user.get("username"),
            }

        for tweet in result.get("data", []):
            author = users_map.get(tweet.get("author_id"), {})
            tweets.append(
                {
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {}),
                    "author": author,
                    "url": f"https://twitter.com/i/web/status/{tweet.get('id')}",
                }
            )

        return {
            "success": True,
            "query": query,
            "tweets": tweets,
            "count": len(tweets),
        }

    except Exception as e:
        logger.error(f"Failed to search tweets: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_get_user_by_username(
    username: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get Twitter user information by username.

    Args:
        username: Twitter username/handle (without @)

    Returns:
        User profile information
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not username:
        return {"success": False, "error": "Username is required"}

    # Remove @ if present
    username = username.lstrip("@")

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        params = {
            "user.fields": "id,name,username,description,location,url,profile_image_url,public_metrics,created_at,verified",
        }

        result = await _make_twitter_request(
            f"/users/by/username/{username}",
            credentials=credentials,
            params=params,
        )

        user_data = result.get("data", {})

        return {
            "success": True,
            "user": {
                "id": user_data.get("id"),
                "name": user_data.get("name"),
                "username": user_data.get("username"),
                "description": user_data.get("description"),
                "location": user_data.get("location"),
                "url": user_data.get("url"),
                "profile_image_url": user_data.get("profile_image_url"),
                "metrics": user_data.get("public_metrics", {}),
                "created_at": user_data.get("created_at"),
                "verified": user_data.get("verified", False),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get Twitter user: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_get_my_profile(
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the authenticated user's profile.

    Returns:
        Authenticated user's profile information
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        params = {
            "user.fields": "id,name,username,description,location,url,profile_image_url,public_metrics,created_at,verified",
        }

        result = await _make_twitter_request(
            "/users/me",
            credentials=credentials,
            params=params,
        )

        user_data = result.get("data", {})

        return {
            "success": True,
            "user": {
                "id": user_data.get("id"),
                "name": user_data.get("name"),
                "username": user_data.get("username"),
                "description": user_data.get("description"),
                "location": user_data.get("location"),
                "url": user_data.get("url"),
                "profile_image_url": user_data.get("profile_image_url"),
                "metrics": user_data.get("public_metrics", {}),
                "created_at": user_data.get("created_at"),
                "verified": user_data.get("verified", False),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get Twitter profile: {e}")
        return {"success": False, "error": str(e)}


async def internal_twitter_delete_tweet(
    tweet_id: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Delete a tweet.
    Requires OAuth 2.0 User Context with tweet.write scope.

    Args:
        tweet_id: ID of the tweet to delete

    Returns:
        Deletion status
    """
    if not runtime_context:
        return {"success": False, "error": "Runtime context is required"}

    if not tweet_id:
        return {"success": False, "error": "Tweet ID is required"}

    try:
        config = config or {}
        tool_name = config.get("_tool_name", "internal_twitter_get_user_timeline")
        credentials = await _get_twitter_credentials(runtime_context, tool_name)

        if credentials.get("token_type") == "app_only":
            return {
                "success": False,
                "error": (
                    "Deleting tweets requires OAuth 2.0 user authentication with tweet.write scope. "
                    "Your current configuration only has an app-only Bearer Token, which is read-only. "
                    "Reconnect via the OAuth flow in My Connections → Twitter."
                ),
            }

        result = await _make_twitter_request(
            f"/tweets/{tweet_id}",
            method="DELETE",
            credentials=credentials,
        )

        deleted = result.get("data", {}).get("deleted", False)

        return {
            "success": True,
            "deleted": deleted,
            "tweet_id": tweet_id,
        }

    except Exception as e:
        logger.error(f"Failed to delete tweet: {e}")
        return {"success": False, "error": str(e)}
