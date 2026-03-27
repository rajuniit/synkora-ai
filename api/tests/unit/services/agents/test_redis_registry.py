"""Unit tests for RedisAgentRegistry."""

import json
from unittest.mock import MagicMock

import pytest

from src.services.agents.redis_registry import RedisAgentRegistry


def _make_redis():
    r = MagicMock()
    pipe = MagicMock()
    r.pipeline.return_value = pipe
    pipe.__enter__ = MagicMock(return_value=pipe)
    pipe.__exit__ = MagicMock(return_value=False)
    return r, pipe


@pytest.mark.unit
class TestKeyHelpers:
    def setup_method(self):
        self.reg = RedisAgentRegistry()

    def test_config_key_format(self):
        key = self.reg._config_key("my-agent")
        assert "my-agent" in key
        assert RedisAgentRegistry.CONFIG_PREFIX in key

    def test_stats_key_format(self):
        key = self.reg._stats_key("my-agent")
        assert "my-agent" in key
        assert RedisAgentRegistry.STATS_PREFIX in key

    def test_different_agents_have_different_keys(self):
        assert self.reg._config_key("agent-a") != self.reg._config_key("agent-b")


@pytest.mark.unit
class TestSanitizeConfig:
    def setup_method(self):
        self.reg = RedisAgentRegistry()

    def test_api_key_redacted(self):
        config = {"api_key": "sk-secret-123", "name": "agent"}
        result = self.reg._sanitize_config(config)
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "agent"

    def test_password_redacted(self):
        config = {"password": "p4ssw0rd"}
        result = self.reg._sanitize_config(config)
        assert result["password"] == "[REDACTED]"

    def test_token_redacted(self):
        config = {"token": "tok-abc"}
        result = self.reg._sanitize_config(config)
        assert result["token"] == "[REDACTED]"

    def test_secret_redacted(self):
        config = {"secret": "shh"}
        result = self.reg._sanitize_config(config)
        assert result["secret"] == "[REDACTED]"

    def test_nested_llm_config_api_key_redacted(self):
        config = {"llm_config": {"api_key": "key-xyz", "model": "gpt-4"}}
        result = self.reg._sanitize_config(config)
        assert result["llm_config"]["api_key"] == "[REDACTED]"
        assert result["llm_config"]["model"] == "gpt-4"

    def test_non_sensitive_fields_preserved(self):
        config = {"name": "test", "type": "llm", "temperature": 0.7}
        result = self.reg._sanitize_config(config)
        assert result == config

    def test_does_not_mutate_original(self):
        config = {"api_key": "original"}
        self.reg._sanitize_config(config)
        assert config["api_key"] == "original"


@pytest.mark.unit
class TestRegisterConfig:
    def test_returns_false_when_redis_unavailable(self):
        reg = RedisAgentRegistry(redis_client=None)
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            result = reg.register_config("agent-1", {"name": "a"})
        assert result is False

    def test_returns_true_on_success(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        result = reg.register_config("agent-1", {"name": "a"})
        assert result is True

    def test_uses_pipeline(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.register_config("agent-1", {"name": "a"})
        r.pipeline.assert_called_once()
        pipe.execute.assert_called_once()

    def test_adds_to_agent_set(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.register_config("agent-xyz", {})
        pipe.sadd.assert_called_once_with(RedisAgentRegistry.AGENT_SET_KEY, "agent-xyz")

    def test_stores_config_with_setex(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.register_config("agent-1", {"name": "test"})
        pipe.setex.assert_called_once()
        key, ttl, data = pipe.setex.call_args[0]
        assert "agent-1" in key
        assert ttl == reg._ttl
        parsed = json.loads(data)
        assert parsed["name"] == "agent-1"

    def test_redis_error_returns_false(self):
        r, pipe = _make_redis()
        pipe.execute.side_effect = Exception("Redis error")
        reg = RedisAgentRegistry(redis_client=r)
        result = reg.register_config("agent-1", {})
        assert result is False


@pytest.mark.unit
class TestUnregister:
    def test_returns_false_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.unregister("agent-1") is False

    def test_returns_true_on_success(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.unregister("agent-1") is True

    def test_removes_from_set(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.unregister("agent-xyz")
        pipe.srem.assert_called_once_with(RedisAgentRegistry.AGENT_SET_KEY, "agent-xyz")

    def test_deletes_config_and_stats_keys(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.unregister("agent-1")
        assert pipe.delete.call_count == 2


@pytest.mark.unit
class TestGetConfig:
    def test_returns_none_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.get_config("agent-1") is None

    def test_returns_none_on_cache_miss(self):
        r, _ = _make_redis()
        r.get.return_value = None
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.get_config("agent-1") is None

    def test_returns_parsed_config(self):
        data = {"name": "agent-1", "config": {}, "metadata": {}}
        r, _ = _make_redis()
        r.get.return_value = json.dumps(data).encode()
        reg = RedisAgentRegistry(redis_client=r)
        result = reg.get_config("agent-1")
        assert result == data


@pytest.mark.unit
class TestListAgents:
    def test_returns_empty_list_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.list_agents() == []

    def test_returns_empty_when_no_agents(self):
        r, _ = _make_redis()
        r.smembers.return_value = set()
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.list_agents() == []

    def test_returns_agent_names(self):
        r, _ = _make_redis()
        r.smembers.return_value = {"agent-a", "agent-b"}
        reg = RedisAgentRegistry(redis_client=r)
        result = reg.list_agents()
        assert set(result) == {"agent-a", "agent-b"}


@pytest.mark.unit
class TestExists:
    def test_returns_false_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.exists("agent-1") is False

    def test_returns_true_when_member(self):
        r, _ = _make_redis()
        r.sismember.return_value = True
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.exists("agent-1") is True

    def test_returns_false_when_not_member(self):
        r, _ = _make_redis()
        r.sismember.return_value = False
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.exists("agent-1") is False


@pytest.mark.unit
class TestUpdateStats:
    def test_returns_false_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.update_stats("agent-1", {}) is False

    def test_returns_true_on_success(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.update_stats("agent-1", {"requests": 1}) is True

    def test_numeric_values_use_hincrbyfloat(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.update_stats("agent-1", {"count": 5, "latency": 0.3})
        assert pipe.hincrbyfloat.call_count == 2

    def test_string_values_use_hset(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.update_stats("agent-1", {"status": "active"})
        pipe.hset.assert_called()


@pytest.mark.unit
class TestRefreshTtl:
    def test_returns_true_on_success(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        assert reg.refresh_ttl("agent-1") is True

    def test_calls_expire_on_config_and_stats_keys(self):
        r, pipe = _make_redis()
        reg = RedisAgentRegistry(redis_client=r)
        reg.refresh_ttl("agent-1")
        assert pipe.expire.call_count == 2


@pytest.mark.unit
class TestClear:
    def test_returns_false_when_redis_unavailable(self):
        reg = RedisAgentRegistry()
        with pytest.MonkeyPatch().context() as m:
            m.setattr(reg, "_get_redis", lambda: None)
            assert reg.clear() is False

    def test_clears_all_keys(self):
        r, pipe = _make_redis()
        r.smembers.return_value = {"a", "b"}
        reg = RedisAgentRegistry(redis_client=r)
        result = reg.clear()
        assert result is True
        # Should delete config + stats for each agent + the set key
        assert pipe.delete.call_count >= 3


@pytest.mark.unit
class TestGlobalRegistry:
    def test_get_redis_registry_returns_singleton(self):
        import src.services.agents.redis_registry as mod

        mod._redis_registry = None
        from src.services.agents.redis_registry import get_redis_registry

        r1 = get_redis_registry()
        r2 = get_redis_registry()
        assert r1 is r2
        mod._redis_registry = None
