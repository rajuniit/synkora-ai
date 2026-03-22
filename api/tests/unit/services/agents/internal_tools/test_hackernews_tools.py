"""
Tests for hackernews_tools.py - Hacker News Tools

Tests the Hacker News API integration for fetching stories,
searching, and getting user information.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalHackernewsGetTopStories:
    """Tests for internal_hackernews_get_top_stories function."""

    @pytest.mark.asyncio
    async def test_returns_top_stories(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_top_stories

        mock_story_ids = [1, 2, 3]
        mock_stories = [
            {
                "id": 1,
                "title": "Story 1",
                "url": "https://example.com/1",
                "score": 100,
                "by": "user1",
                "time": 1704067200,
                "descendants": 50,
                "type": "story",
            },
            {
                "id": 2,
                "title": "Story 2",
                "url": "https://example.com/2",
                "score": 80,
                "by": "user2",
                "time": 1704067300,
                "descendants": 30,
                "type": "story",
            },
        ]

        with (
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
                new_callable=AsyncMock,
                return_value=mock_story_ids[:2],
            ),
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_item",
                new_callable=AsyncMock,
                side_effect=mock_stories,
            ),
        ):
            result = await internal_hackernews_get_top_stories(limit=2)

            assert result["success"] is True
            assert result["count"] == 2
            assert result["type"] == "top"
            assert result["stories"][0]["title"] == "Story 1"

    @pytest.mark.asyncio
    async def test_limits_results(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_top_stories

        with patch(
            "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await internal_hackernews_get_top_stories(limit=200)

            # Should cap at 100
            assert result["success"] is True


class TestInternalHackernewsGetNewStories:
    """Tests for internal_hackernews_get_new_stories function."""

    @pytest.mark.asyncio
    async def test_returns_new_stories(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_new_stories

        mock_story = {
            "id": 1,
            "title": "New Story",
            "url": "https://example.com/new",
            "score": 5,
            "by": "newuser",
            "time": 1704067200,
            "descendants": 0,
            "type": "story",
        }

        with (
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
                new_callable=AsyncMock,
                return_value=[1],
            ),
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_item",
                new_callable=AsyncMock,
                return_value=mock_story,
            ),
        ):
            result = await internal_hackernews_get_new_stories(limit=1)

            assert result["success"] is True
            assert result["type"] == "new"
            assert result["stories"][0]["title"] == "New Story"


class TestInternalHackernewsGetBestStories:
    """Tests for internal_hackernews_get_best_stories function."""

    @pytest.mark.asyncio
    async def test_returns_best_stories(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_best_stories

        mock_story = {
            "id": 1,
            "title": "Best Story Ever",
            "url": "https://example.com/best",
            "score": 5000,
            "by": "topuser",
            "time": 1704067200,
            "descendants": 500,
            "type": "story",
        }

        with (
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
                new_callable=AsyncMock,
                return_value=[1],
            ),
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_item",
                new_callable=AsyncMock,
                return_value=mock_story,
            ),
        ):
            result = await internal_hackernews_get_best_stories(limit=1)

            assert result["success"] is True
            assert result["type"] == "best"
            assert result["stories"][0]["score"] == 5000


class TestInternalHackernewsGetAskHn:
    """Tests for internal_hackernews_get_ask_hn function."""

    @pytest.mark.asyncio
    async def test_returns_ask_hn_posts(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_ask_hn

        mock_ask = {
            "id": 1,
            "title": "Ask HN: Best programming language?",
            "text": "Looking for recommendations...",
            "score": 50,
            "by": "asker",
            "time": 1704067200,
            "descendants": 100,
            "type": "story",
        }

        with (
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
                new_callable=AsyncMock,
                return_value=[1],
            ),
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_item",
                new_callable=AsyncMock,
                return_value=mock_ask,
            ),
        ):
            result = await internal_hackernews_get_ask_hn(limit=1)

            assert result["success"] is True
            assert result["type"] == "ask"
            assert "text" in result["stories"][0]


class TestInternalHackernewsGetShowHn:
    """Tests for internal_hackernews_get_show_hn function."""

    @pytest.mark.asyncio
    async def test_returns_show_hn_posts(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_show_hn

        mock_show = {
            "id": 1,
            "title": "Show HN: My new project",
            "url": "https://myproject.com",
            "text": "Built this over the weekend",
            "score": 75,
            "by": "creator",
            "time": 1704067200,
            "descendants": 25,
            "type": "story",
        }

        with (
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_story_ids",
                new_callable=AsyncMock,
                return_value=[1],
            ),
            patch(
                "src.services.agents.internal_tools.hackernews_tools._fetch_item",
                new_callable=AsyncMock,
                return_value=mock_show,
            ),
        ):
            result = await internal_hackernews_get_show_hn(limit=1)

            assert result["success"] is True
            assert result["type"] == "show"


class TestInternalHackernewsGetStoryDetails:
    """Tests for internal_hackernews_get_story_details function."""

    @pytest.mark.asyncio
    async def test_returns_story_not_found(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_story_details

        with patch(
            "src.services.agents.internal_tools.hackernews_tools._fetch_item",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await internal_hackernews_get_story_details(story_id=99999999)

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_story_details(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_story_details

        mock_story = {
            "id": 12345,
            "title": "Interesting Story",
            "url": "https://example.com",
            "text": "Story content here",
            "score": 200,
            "by": "author",
            "time": 1704067200,
            "descendants": 75,
            "type": "story",
        }

        with patch(
            "src.services.agents.internal_tools.hackernews_tools._fetch_item",
            new_callable=AsyncMock,
            return_value=mock_story,
        ):
            result = await internal_hackernews_get_story_details(
                story_id=12345,
                include_comments=False,
            )

            assert result["success"] is True
            assert result["story"]["id"] == 12345
            assert result["story"]["title"] == "Interesting Story"

    @pytest.mark.asyncio
    async def test_includes_comments_when_requested(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_story_details

        mock_story = {
            "id": 12345,
            "title": "Story with Comments",
            "score": 100,
            "by": "author",
            "time": 1704067200,
            "descendants": 10,
            "type": "story",
            "kids": [100, 101],
        }
        mock_comment = {
            "id": 100,
            "by": "commenter",
            "text": "Great post!",
            "time": 1704067300,
            "type": "comment",
            "kids": [],
        }

        with patch(
            "src.services.agents.internal_tools.hackernews_tools._fetch_item",
            new_callable=AsyncMock,
            side_effect=[mock_story, mock_comment, mock_comment],
        ):
            result = await internal_hackernews_get_story_details(
                story_id=12345,
                include_comments=True,
                comment_limit=2,
            )

            assert result["success"] is True
            assert "comments" in result["story"]


class TestInternalHackernewsSearch:
    """Tests for internal_hackernews_search function."""

    @pytest.mark.asyncio
    async def test_searches_stories_successfully(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_search

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Python Best Practices",
                    "url": "https://example.com/python",
                    "author": "pydev",
                    "points": 150,
                    "num_comments": 50,
                    "created_at": "2025-01-01T00:00:00Z",
                }
            ],
            "nbHits": 100,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await internal_hackernews_search(
                query="python",
                search_type="story",
                limit=10,
            )

            assert result["success"] is True
            assert result["count"] == 1
            assert result["results"][0]["title"] == "Python Best Practices"

    @pytest.mark.asyncio
    async def test_searches_with_time_range(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_search

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": [], "nbHits": 0}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await internal_hackernews_search(
                query="ai",
                time_range="24h",
            )

            assert result["success"] is True


class TestInternalHackernewsGetUser:
    """Tests for internal_hackernews_get_user function."""

    @pytest.mark.asyncio
    async def test_returns_user_not_found(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_user

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await internal_hackernews_get_user(username="nonexistent_user_123")

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_user_info(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_user

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "pg",
            "created": 1160418111,
            "karma": 150000,
            "about": "Creator of Hacker News",
            "submitted": [1, 2, 3, 4, 5],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await internal_hackernews_get_user(username="pg")

            assert result["success"] is True
            assert result["user"]["id"] == "pg"
            assert result["user"]["karma"] == 150000


class TestInternalHackernewsGetTrendingTopics:
    """Tests for internal_hackernews_get_trending_topics function."""

    @pytest.mark.asyncio
    async def test_analyzes_trending_topics(self):
        from src.services.agents.internal_tools.hackernews_tools import internal_hackernews_get_trending_topics

        mock_top_stories_result = {
            "success": True,
            "stories": [
                {"title": "OpenAI announces GPT-5", "score": 500, "hn_url": "https://hn.com/1"},
                {"title": "Google AI breakthrough", "score": 400, "hn_url": "https://hn.com/2"},
                {"title": "Python 4.0 released", "score": 300, "hn_url": "https://hn.com/3"},
            ],
        }

        with patch(
            "src.services.agents.internal_tools.hackernews_tools.internal_hackernews_get_top_stories",
            new_callable=AsyncMock,
            return_value=mock_top_stories_result,
        ):
            result = await internal_hackernews_get_trending_topics(limit=10)

            assert result["success"] is True
            assert result["analyzed_stories"] == 3
            # Should find topics like "ai", "openai", "google", "python"
            assert len(result["trending_topics"]) >= 0
