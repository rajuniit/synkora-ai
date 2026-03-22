"""
Hacker News Tools for tech news monitoring and trend discovery.
Uses the official Hacker News API (no authentication required).

This tool enables:
- Fetching top/new/best stories
- Getting story details and comments
- Searching for specific topics
- Monitoring trends in tech community

API Reference: https://github.com/HackerNews/API
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA_API = "https://hn.algolia.com/api/v1"


async def _fetch_item(item_id: int) -> dict[str, Any] | None:
    """Fetch a single item (story, comment, etc.) by ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HN_API_BASE}/item/{item_id}.json", timeout=30.0)
        if response.status_code == 200:
            return response.json()
        return None


async def _fetch_story_ids(endpoint: str, limit: int = 30) -> list[int]:
    """Fetch story IDs from a specific endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HN_API_BASE}/{endpoint}.json", timeout=30.0)
        if response.status_code == 200:
            ids = response.json()
            return ids[:limit] if ids else []
        return []


async def internal_hackernews_get_top_stories(
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the current top stories on Hacker News.
    These are the stories currently on the front page.

    Args:
        limit: Maximum number of stories to return (default 10, max 100)

    Returns:
        List of top stories with titles, URLs, scores, and metadata
    """
    try:
        limit = min(limit, 100)
        story_ids = await _fetch_story_ids("topstories", limit)

        stories = []
        for story_id in story_ids:
            item = await _fetch_item(story_id)
            if item and item.get("type") == "story":
                stories.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "score": item.get("score", 0),
                        "by": item.get("by"),
                        "time": item.get("time"),
                        "descendants": item.get("descendants", 0),  # comment count
                        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                    }
                )

        return {
            "success": True,
            "stories": stories,
            "count": len(stories),
            "type": "top",
        }

    except Exception as e:
        logger.error(f"Failed to get HN top stories: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_new_stories(
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the newest stories on Hacker News.

    Args:
        limit: Maximum number of stories to return (default 10, max 100)

    Returns:
        List of newest stories
    """
    try:
        limit = min(limit, 100)
        story_ids = await _fetch_story_ids("newstories", limit)

        stories = []
        for story_id in story_ids:
            item = await _fetch_item(story_id)
            if item and item.get("type") == "story":
                stories.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "score": item.get("score", 0),
                        "by": item.get("by"),
                        "time": item.get("time"),
                        "descendants": item.get("descendants", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                    }
                )

        return {
            "success": True,
            "stories": stories,
            "count": len(stories),
            "type": "new",
        }

    except Exception as e:
        logger.error(f"Failed to get HN new stories: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_best_stories(
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get the best stories on Hacker News (highest voted over time).

    Args:
        limit: Maximum number of stories to return (default 10, max 100)

    Returns:
        List of best stories
    """
    try:
        limit = min(limit, 100)
        story_ids = await _fetch_story_ids("beststories", limit)

        stories = []
        for story_id in story_ids:
            item = await _fetch_item(story_id)
            if item and item.get("type") == "story":
                stories.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "score": item.get("score", 0),
                        "by": item.get("by"),
                        "time": item.get("time"),
                        "descendants": item.get("descendants", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                    }
                )

        return {
            "success": True,
            "stories": stories,
            "count": len(stories),
            "type": "best",
        }

    except Exception as e:
        logger.error(f"Failed to get HN best stories: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_ask_hn(
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get Ask HN posts - questions from the community.

    Args:
        limit: Maximum number of posts to return (default 10, max 100)

    Returns:
        List of Ask HN posts
    """
    try:
        limit = min(limit, 100)
        story_ids = await _fetch_story_ids("askstories", limit)

        stories = []
        for story_id in story_ids:
            item = await _fetch_item(story_id)
            if item:
                stories.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "text": item.get("text"),  # Ask HN posts have text content
                        "score": item.get("score", 0),
                        "by": item.get("by"),
                        "time": item.get("time"),
                        "descendants": item.get("descendants", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                    }
                )

        return {
            "success": True,
            "stories": stories,
            "count": len(stories),
            "type": "ask",
        }

    except Exception as e:
        logger.error(f"Failed to get Ask HN posts: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_show_hn(
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get Show HN posts - projects shared by the community.

    Args:
        limit: Maximum number of posts to return (default 10, max 100)

    Returns:
        List of Show HN posts
    """
    try:
        limit = min(limit, 100)
        story_ids = await _fetch_story_ids("showstories", limit)

        stories = []
        for story_id in story_ids:
            item = await _fetch_item(story_id)
            if item:
                stories.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "text": item.get("text"),
                        "score": item.get("score", 0),
                        "by": item.get("by"),
                        "time": item.get("time"),
                        "descendants": item.get("descendants", 0),
                        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
                    }
                )

        return {
            "success": True,
            "stories": stories,
            "count": len(stories),
            "type": "show",
        }

    except Exception as e:
        logger.error(f"Failed to get Show HN posts: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_story_details(
    story_id: int,
    include_comments: bool = False,
    comment_limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get detailed information about a specific story.

    Args:
        story_id: The Hacker News story ID
        include_comments: Whether to fetch top-level comments (default False)
        comment_limit: Max number of comments to fetch if include_comments is True

    Returns:
        Story details with optional comments
    """
    try:
        item = await _fetch_item(story_id)

        if not item:
            return {"success": False, "error": f"Story {story_id} not found"}

        story = {
            "id": item.get("id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "text": item.get("text"),
            "score": item.get("score", 0),
            "by": item.get("by"),
            "time": item.get("time"),
            "descendants": item.get("descendants", 0),
            "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
            "type": item.get("type"),
        }

        # Fetch comments if requested
        if include_comments and item.get("kids"):
            comments = []
            comment_ids = item.get("kids", [])[:comment_limit]

            for comment_id in comment_ids:
                comment = await _fetch_item(comment_id)
                if comment and comment.get("type") == "comment":
                    comments.append(
                        {
                            "id": comment.get("id"),
                            "by": comment.get("by"),
                            "text": comment.get("text"),
                            "time": comment.get("time"),
                            "replies": len(comment.get("kids", [])),
                        }
                    )

            story["comments"] = comments
            story["comment_count_fetched"] = len(comments)

        return {
            "success": True,
            "story": story,
        }

    except Exception as e:
        logger.error(f"Failed to get HN story details: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_search(
    query: str,
    search_type: str = "story",
    sort_by: str = "relevance",
    time_range: str | None = None,
    limit: int = 10,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Search Hacker News using Algolia search API.

    Args:
        query: Search query string
        search_type: "story", "comment", or "all" (default: story)
        sort_by: "relevance" or "date" (default: relevance)
        time_range: Filter by time - "24h", "week", "month", "year", or None for all time
        limit: Maximum results (default 10, max 100)

    Returns:
        Search results with matching stories/comments
    """
    try:
        limit = min(limit, 100)

        # Build search parameters
        params = {
            "query": query,
            "hitsPerPage": limit,
        }

        # Filter by type
        if search_type == "story":
            params["tags"] = "story"
        elif search_type == "comment":
            params["tags"] = "comment"
        # "all" doesn't need a tag filter

        # Time range filter
        if time_range:
            import time

            now = int(time.time())
            time_filters = {
                "24h": now - 86400,
                "week": now - 604800,
                "month": now - 2592000,
                "year": now - 31536000,
            }
            if time_range in time_filters:
                params["numericFilters"] = f"created_at_i>{time_filters[time_range]}"

        # Choose endpoint based on sort
        endpoint = "search" if sort_by == "relevance" else "search_by_date"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HN_ALGOLIA_API}/{endpoint}",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for hit in data.get("hits", []):
            result = {
                "id": hit.get("objectID"),
                "title": hit.get("title"),
                "url": hit.get("url"),
                "author": hit.get("author"),
                "points": hit.get("points"),
                "num_comments": hit.get("num_comments"),
                "created_at": hit.get("created_at"),
                "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            }

            # For comments, include the comment text
            if search_type == "comment":
                result["comment_text"] = hit.get("comment_text")
                result["story_title"] = hit.get("story_title")
                result["story_id"] = hit.get("story_id")

            results.append(result)

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "total_hits": data.get("nbHits", 0),
        }

    except Exception as e:
        logger.error(f"Failed to search HN: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_user(
    username: str,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Get information about a Hacker News user.

    Args:
        username: The HN username

    Returns:
        User profile information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HN_API_BASE}/user/{username}.json",
                timeout=30.0,
            )

            if response.status_code == 200:
                user = response.json()

                if not user:
                    return {"success": False, "error": f"User '{username}' not found"}

                return {
                    "success": True,
                    "user": {
                        "id": user.get("id"),
                        "created": user.get("created"),
                        "karma": user.get("karma"),
                        "about": user.get("about"),
                        "submitted_count": len(user.get("submitted", [])),
                        "profile_url": f"https://news.ycombinator.com/user?id={user.get('id')}",
                    },
                }
            else:
                return {"success": False, "error": f"User '{username}' not found"}

    except Exception as e:
        logger.error(f"Failed to get HN user: {e}")
        return {"success": False, "error": str(e)}


async def internal_hackernews_get_trending_topics(
    limit: int = 20,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Analyze current top stories to identify trending topics.
    This provides a summary of what's trending on HN right now.

    Args:
        limit: Number of top stories to analyze (default 20)

    Returns:
        List of trending topics with example stories
    """
    try:
        # Get top stories
        result = await internal_hackernews_get_top_stories(
            limit=limit,
            config=config,
            runtime_context=runtime_context,
        )

        if not result.get("success"):
            return result

        stories = result.get("stories", [])

        # Simple keyword extraction from titles
        # In production, you might use NLP or the Algolia tags
        keywords = {}
        tech_terms = [
            "ai",
            "llm",
            "gpt",
            "openai",
            "anthropic",
            "google",
            "microsoft",
            "apple",
            "rust",
            "python",
            "javascript",
            "typescript",
            "go",
            "java",
            "startup",
            "vc",
            "funding",
            "acquisition",
            "security",
            "privacy",
            "hack",
            "breach",
            "open source",
            "github",
            "linux",
            "aws",
            "cloud",
            "kubernetes",
            "docker",
            "crypto",
            "bitcoin",
            "blockchain",
            "remote",
            "layoff",
            "hiring",
        ]

        for story in stories:
            title = story.get("title", "").lower()
            for term in tech_terms:
                if term in title:
                    if term not in keywords:
                        keywords[term] = []
                    keywords[term].append(
                        {
                            "title": story.get("title"),
                            "score": story.get("score"),
                            "hn_url": story.get("hn_url"),
                        }
                    )

        # Sort by number of stories mentioning each topic
        trending = [
            {
                "topic": topic,
                "story_count": len(story_list),
                "total_score": sum(s.get("score", 0) for s in story_list),
                "stories": story_list[:3],  # Top 3 examples
            }
            for topic, story_list in sorted(
                keywords.items(),
                key=lambda x: (len(x[1]), sum(s.get("score", 0) for s in x[1])),
                reverse=True,
            )
        ]

        return {
            "success": True,
            "trending_topics": trending[:10],  # Top 10 trending topics
            "analyzed_stories": len(stories),
        }

    except Exception as e:
        logger.error(f"Failed to get HN trending topics: {e}")
        return {"success": False, "error": str(e)}
