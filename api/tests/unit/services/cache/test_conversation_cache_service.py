"""Unit tests for ConversationCacheService."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.services.cache.conversation_cache_service import ConversationCacheService


def _make_service(redis_mock=None):
    """Return a service instance with an optional Redis mock."""
    return ConversationCacheService(redis_client=redis_mock)


def _make_redis():
    """Return a MagicMock that behaves like a sync Redis client."""
    r = MagicMock()
    r.get.return_value = None
    r.setex.return_value = True
    r.delete.return_value = 1
    return r


@pytest.mark.unit
class TestBuildKey:
    def test_key_format(self):
        svc = _make_service()
        key = svc._build_key("prefix", "conv-123")
        assert key == "prefix:conv-123"


@pytest.mark.unit
class TestSerializeMessage:
    def setup_method(self):
        self.svc = _make_service()

    def test_plain_string_values_pass_through(self):
        msg = {"role": "user", "content": "hello"}
        result = self.svc._serialize_message(msg)
        assert result == msg

    def test_uuid_converted_to_string(self):
        uid = uuid.uuid4()
        msg = {"id": uid, "role": "assistant"}
        result = self.svc._serialize_message(msg)
        assert isinstance(result["id"], str)
        assert result["id"] == str(uid)

    def test_datetime_converted_to_isoformat(self):
        now = datetime(2024, 1, 15, 12, 0, 0)
        msg = {"created_at": now, "role": "user"}
        result = self.svc._serialize_message(msg)
        assert result["created_at"] == now.isoformat()

    def test_nested_dict_serialized_recursively(self):
        uid = uuid.uuid4()
        msg = {"meta": {"id": uid}}
        result = self.svc._serialize_message(msg)
        assert isinstance(result["meta"]["id"], str)

    def test_list_of_dicts_serialized(self):
        uid = uuid.uuid4()
        msg = {"parts": [{"id": uid}]}
        result = self.svc._serialize_message(msg)
        assert isinstance(result["parts"][0]["id"], str)

    def test_list_of_primitives_unchanged(self):
        msg = {"tags": ["a", "b", "c"]}
        result = self.svc._serialize_message(msg)
        assert result["tags"] == ["a", "b", "c"]


@pytest.mark.unit
class TestGetConversationHistory:
    @pytest.mark.asyncio
    async def test_returns_none_when_redis_unavailable(self):
        svc = _make_service(redis_mock=None)
        with patch.object(svc, "_get_redis", return_value=None):
            result = await svc.get_conversation_history("conv-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self):
        redis = _make_redis()
        redis.get.return_value = None
        svc = _make_service(redis)
        result = await svc.get_conversation_history("conv-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_messages(self):
        messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        redis = _make_redis()
        redis.get.return_value = json.dumps(messages).encode()
        svc = _make_service(redis)
        result = await svc.get_conversation_history("conv-1")
        assert result == messages

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        messages = [{"role": "user", "content": str(i)} for i in range(30)]
        redis = _make_redis()
        redis.get.return_value = json.dumps(messages).encode()
        svc = _make_service(redis)
        result = await svc.get_conversation_history("conv-1", limit=10)
        assert len(result) == 10
        assert result[-1]["content"] == "29"

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_error(self):
        redis = _make_redis()
        redis.get.side_effect = Exception("Redis down")
        svc = _make_service(redis)
        result = await svc.get_conversation_history("conv-1")
        assert result is None


@pytest.mark.unit
class TestSetConversationHistory:
    @pytest.mark.asyncio
    async def test_returns_false_when_redis_unavailable(self):
        svc = _make_service(None)
        with patch.object(svc, "_get_redis", return_value=None):
            result = await svc.set_conversation_history("conv-1", [])
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        redis = _make_redis()
        svc = _make_service(redis)
        result = await svc.set_conversation_history("conv-1", [{"role": "user", "content": "x"}])
        assert result is True
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_trims_to_max_cached_messages(self):
        redis = _make_redis()
        svc = _make_service(redis)
        messages = [{"role": "user", "content": str(i)} for i in range(100)]
        await svc.set_conversation_history("conv-1", messages)
        call_args = redis.setex.call_args
        stored = json.loads(call_args[0][2])
        assert len(stored) == ConversationCacheService.MAX_CACHED_MESSAGES

    @pytest.mark.asyncio
    async def test_custom_ttl_used(self):
        redis = _make_redis()
        svc = _make_service(redis)
        await svc.set_conversation_history("conv-1", [], ttl=999)
        call_args = redis.setex.call_args[0]
        # Second positional arg is the timedelta
        from datetime import timedelta

        assert call_args[1] == timedelta(seconds=999)


@pytest.mark.unit
class TestAppendMessage:
    @pytest.mark.asyncio
    async def test_appends_to_empty_cache(self):
        redis = _make_redis()
        redis.get.return_value = None
        svc = _make_service(redis)
        result = await svc.append_message("conv-1", {"role": "user", "content": "hi"})
        assert result is True
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_appends_to_existing_messages(self):
        existing = [{"role": "user", "content": "existing"}]
        redis = _make_redis()
        redis.get.return_value = json.dumps(existing).encode()
        svc = _make_service(redis)
        await svc.append_message("conv-1", {"role": "assistant", "content": "new"})
        call_args = redis.setex.call_args[0]
        stored = json.loads(call_args[2])
        assert len(stored) == 2
        assert stored[-1]["content"] == "new"

    @pytest.mark.asyncio
    async def test_trims_when_exceeds_max(self):
        existing = [{"role": "user", "content": str(i)} for i in range(ConversationCacheService.MAX_CACHED_MESSAGES)]
        redis = _make_redis()
        redis.get.return_value = json.dumps(existing).encode()
        svc = _make_service(redis)
        await svc.append_message("conv-1", {"role": "assistant", "content": "extra"})
        call_args = redis.setex.call_args[0]
        stored = json.loads(call_args[2])
        assert len(stored) == ConversationCacheService.MAX_CACHED_MESSAGES


@pytest.mark.unit
class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_deletes_all_keys(self):
        redis = _make_redis()
        svc = _make_service(redis)
        await svc.invalidate("conv-1")
        redis.delete.assert_called_once()
        deleted_keys = redis.delete.call_args[0]
        assert any("conv_history" in k for k in deleted_keys)
        assert any("conv_summary" in k for k in deleted_keys)
        assert any("conv_meta" in k for k in deleted_keys)

    @pytest.mark.asyncio
    async def test_invalidate_history_only_deletes_one_key(self):
        redis = _make_redis()
        svc = _make_service(redis)
        await svc.invalidate_history_only("conv-1")
        redis.delete.assert_called_once()
        deleted_key = redis.delete.call_args[0][0]
        assert "conv_history" in deleted_key


@pytest.mark.unit
class TestSummaryAndMetadata:
    @pytest.mark.asyncio
    async def test_get_summary_returns_cached_string(self):
        redis = _make_redis()
        redis.get.return_value = b"A summary of the conversation."
        svc = _make_service(redis)
        result = await svc.get_conversation_summary("conv-1")
        assert result == "A summary of the conversation."

    @pytest.mark.asyncio
    async def test_set_summary_uses_summary_ttl_by_default(self):
        redis = _make_redis()
        svc = _make_service(redis)
        await svc.set_conversation_summary("conv-1", "summary text")
        call_args = redis.setex.call_args[0]
        from datetime import timedelta

        assert call_args[1] == timedelta(seconds=ConversationCacheService.SUMMARY_TTL)

    @pytest.mark.asyncio
    async def test_get_metadata_returns_dict(self):
        meta = {"total_messages": 42}
        redis = _make_redis()
        redis.get.return_value = json.dumps(meta).encode()
        svc = _make_service(redis)
        result = await svc.get_conversation_metadata("conv-1")
        assert result == meta

    @pytest.mark.asyncio
    async def test_update_metadata_field_creates_if_missing(self):
        redis = _make_redis()
        redis.get.return_value = None  # no existing metadata
        svc = _make_service(redis)
        result = await svc.update_metadata_field("conv-1", "page", 5)
        assert result is True
        stored = json.loads(redis.setex.call_args[0][2])
        assert stored["page"] == 5
