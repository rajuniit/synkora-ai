"""
Tests for twitter_tools.py - Twitter/X Tools

Tests the Twitter API integration for timeline, bookmarks, posting,
searching, and user operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalTwitterGetUserTimeline:
    """Tests for internal_twitter_get_user_timeline function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_timeline

        result = await internal_twitter_get_user_timeline(
            user_id="123456",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_user_id_or_username(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_timeline

        mock_credentials = {"bearer_token": "test-token"}

        with patch(
            "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
            new_callable=AsyncMock,
            return_value=mock_credentials,
        ):
            result = await internal_twitter_get_user_timeline(runtime_context={"agent_id": "test"})

            assert result["success"] is False
            assert "user_id or username is required" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_timeline_successfully(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_timeline

        mock_credentials = {"bearer_token": "test-token"}

        mock_response_data = {
            "data": [
                {
                    "id": "tweet-1",
                    "text": "Hello world!",
                    "created_at": "2025-01-10T10:00:00Z",
                    "public_metrics": {"like_count": 10},
                    "author_id": "123456",
                }
            ]
        }

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_get_user_timeline(
                user_id="123456",
                max_results=10,
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["count"] == 1
            assert result["tweets"][0]["id"] == "tweet-1"


class TestInternalTwitterGetBookmarks:
    """Tests for internal_twitter_get_bookmarks function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_bookmarks

        result = await internal_twitter_get_bookmarks(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalTwitterPostTweet:
    """Tests for internal_twitter_post_tweet function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_post_tweet

        result = await internal_twitter_post_tweet(
            text="Hello world!",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_text(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_post_tweet

        result = await internal_twitter_post_tweet(
            text="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Tweet text is required" in result["error"]

    @pytest.mark.asyncio
    async def test_validates_character_limit(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_post_tweet

        long_text = "x" * 281

        result = await internal_twitter_post_tweet(
            text=long_text,
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "280 characters" in result["error"]

    @pytest.mark.asyncio
    async def test_posts_tweet_successfully(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_post_tweet

        mock_credentials = {"bearer_token": "test-token"}
        mock_response_data = {
            "data": {
                "id": "tweet-123",
                "text": "Hello world!",
            }
        }

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_post_tweet(
                text="Hello world!",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["tweet"]["id"] == "tweet-123"
            assert "url" in result


class TestInternalTwitterSearchTweets:
    """Tests for internal_twitter_search_tweets function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_search_tweets

        result = await internal_twitter_search_tweets(
            query="python",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_query(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_search_tweets

        result = await internal_twitter_search_tweets(
            query="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "query is required" in result["error"]

    @pytest.mark.asyncio
    async def test_searches_tweets_successfully(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_search_tweets

        mock_credentials = {"bearer_token": "test-token"}
        mock_response_data = {
            "data": [
                {
                    "id": "tweet-1",
                    "text": "Python is great!",
                    "created_at": "2025-01-10T10:00:00Z",
                    "public_metrics": {"like_count": 50},
                    "author_id": "user-1",
                }
            ],
            "includes": {"users": [{"id": "user-1", "name": "Dev User", "username": "devuser"}]},
        }

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_search_tweets(
                query="python",
                max_results=10,
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["count"] == 1
            assert result["tweets"][0]["text"] == "Python is great!"


class TestInternalTwitterGetUserByUsername:
    """Tests for internal_twitter_get_user_by_username function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_by_username

        result = await internal_twitter_get_user_by_username(
            username="testuser",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_username(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_by_username

        result = await internal_twitter_get_user_by_username(
            username="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Username is required" in result["error"]

    @pytest.mark.asyncio
    async def test_strips_at_symbol(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_user_by_username

        mock_credentials = {"bearer_token": "test-token"}
        mock_response_data = {
            "data": {
                "id": "123",
                "name": "Test User",
                "username": "testuser",
            }
        }

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_get_user_by_username(
                username="@testuser",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["user"]["username"] == "testuser"


class TestInternalTwitterGetMyProfile:
    """Tests for internal_twitter_get_my_profile function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_my_profile

        result = await internal_twitter_get_my_profile(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_profile_successfully(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_get_my_profile

        mock_credentials = {"bearer_token": "test-token"}
        mock_response_data = {
            "data": {
                "id": "123456",
                "name": "My Profile",
                "username": "myprofile",
                "description": "Test bio",
                "public_metrics": {"followers_count": 100},
            }
        }

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_get_my_profile(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["user"]["id"] == "123456"
            assert result["user"]["username"] == "myprofile"


class TestInternalTwitterDeleteTweet:
    """Tests for internal_twitter_delete_tweet function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_delete_tweet

        result = await internal_twitter_delete_tweet(
            tweet_id="123",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_tweet_id(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_delete_tweet

        result = await internal_twitter_delete_tweet(
            tweet_id="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Tweet ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_deletes_tweet_successfully(self):
        from src.services.agents.internal_tools.twitter_tools import internal_twitter_delete_tweet

        mock_credentials = {"bearer_token": "test-token"}
        mock_response_data = {"data": {"deleted": True}}

        with (
            patch(
                "src.services.agents.internal_tools.twitter_tools._get_twitter_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.twitter_tools._make_twitter_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_twitter_delete_tweet(
                tweet_id="tweet-123",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["deleted"] is True
