"""
Unit tests for llm_response_cache.

Validates all 6 correctness gates.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROVIDER = "openai"
MODEL = "gpt-4o-mini"
TEMP = 0.0
SYS_HASH = "abcd1234"
AGENT_TS = "1700000000.0"

MESSAGES_SIMPLE = [{"role": "user", "content": "What is 2+2?"}]


class TestIsCacheable:
    def test_deterministic_cacheable(self):
        from src.services.cache.llm_response_cache import _is_cacheable

        assert _is_cacheable(MESSAGES_SIMPLE, 0.0) is True

    def test_high_temp_skipped(self):
        from src.services.cache.llm_response_cache import _is_cacheable

        assert _is_cacheable(MESSAGES_SIMPLE, 0.7) is False

    def test_time_sensitive_skipped(self):
        from src.services.cache.llm_response_cache import _is_cacheable

        for kw in ["today", "now", "current", "latest", "live", "real-time"]:
            msgs = [{"role": "user", "content": f"What is {kw}?"}]
            assert _is_cacheable(msgs, 0.0) is False, f"keyword '{kw}' should block cache"

    def test_tool_role_skipped(self):
        from src.services.cache.llm_response_cache import _is_cacheable

        msgs = [
            {"role": "user", "content": "search for something"},
            {"role": "tool", "content": "search result"},
        ]
        assert _is_cacheable(msgs, 0.0) is False

    def test_tool_calls_skipped(self):
        from src.services.cache.llm_response_cache import _is_cacheable

        msgs = [{"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]}]
        assert _is_cacheable(msgs, 0.0) is False


class TestMakeCacheKey:
    def test_different_agent_updated_at_gives_different_key(self):
        from src.services.cache.llm_response_cache import _make_cache_key

        key1 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, "100.0")
        key2 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, "200.0")
        assert key1 != key2

    def test_different_system_prompt_hash_gives_different_key(self):
        from src.services.cache.llm_response_cache import _make_cache_key

        key1 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, "hash1", AGENT_TS)
        key2 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, "hash2", AGENT_TS)
        assert key1 != key2

    def test_same_inputs_same_key(self):
        from src.services.cache.llm_response_cache import _make_cache_key

        key1 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, AGENT_TS)
        key2 = _make_cache_key(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, AGENT_TS)
        assert key1 == key2


class TestGetSetCachedResponse:
    @pytest.mark.asyncio
    async def test_redis_down_fail_open(self):
        """If Redis is unavailable, get_cached_response returns None (not an exception)."""
        with patch("src.services.cache.llm_response_cache.get_redis_async", side_effect=Exception("redis down")):
            # Should not raise
            from src.services.cache.llm_response_cache import get_cached_response

            result = await get_cached_response(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, AGENT_TS)
            assert result is None

    @pytest.mark.asyncio
    async def test_set_redis_down_fail_open(self):
        """If Redis is unavailable, set_cached_response silently passes."""
        with patch("src.services.cache.llm_response_cache.get_redis_async", side_effect=Exception("redis down")):
            from src.services.cache.llm_response_cache import set_cached_response

            # Must not raise
            await set_cached_response(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, "response", SYS_HASH, AGENT_TS)

    @pytest.mark.asyncio
    async def test_size_cap_prevents_large_response(self):
        """Responses > 50 KB are not cached."""
        mock_redis = AsyncMock()

        with patch("src.services.cache.llm_response_cache.get_redis_async", return_value=mock_redis):
            from src.services.cache.llm_response_cache import set_cached_response

            large_response = "x" * 60_000  # > 50 KB
            await set_cached_response(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, large_response, SYS_HASH, AGENT_TS)
            mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_value(self):
        """get_cached_response returns cached string on hit."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"Paris")

        with patch("src.services.cache.llm_response_cache.get_redis_async", return_value=mock_redis):
            from src.services.cache.llm_response_cache import get_cached_response

            result = await get_cached_response(PROVIDER, MODEL, TEMP, MESSAGES_SIMPLE, SYS_HASH, AGENT_TS)
            assert result == "Paris"

    @pytest.mark.asyncio
    async def test_uncacheable_skips_redis(self):
        """Time-sensitive queries never reach Redis."""
        mock_redis = AsyncMock()

        with patch("src.services.cache.llm_response_cache.get_redis_async", return_value=mock_redis):
            from src.services.cache.llm_response_cache import get_cached_response

            msgs = [{"role": "user", "content": "What is today's stock price?"}]
            result = await get_cached_response(PROVIDER, MODEL, TEMP, msgs, SYS_HASH, AGENT_TS)
            assert result is None
            mock_redis.get.assert_not_called()
