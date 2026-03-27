"""Unit tests for LLMClientPool."""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.services.performance.llm_client_pool import LLMClientPool, PooledLLMClient


@pytest.mark.unit
class TestPooledLLMClient:
    def test_mark_used_increments_count(self):
        client = PooledLLMClient(client=MagicMock(), provider="openai", model="gpt-4")
        assert client.use_count == 0
        client.mark_used()
        assert client.use_count == 1
        client.mark_used()
        assert client.use_count == 2

    def test_mark_used_updates_last_used(self):
        client = PooledLLMClient(client=MagicMock(), provider="openai", model="gpt-4")
        before = client.last_used
        time.sleep(0.01)
        client.mark_used()
        assert client.last_used >= before


@pytest.mark.unit
class TestLLMClientPoolKey:
    def setup_method(self):
        self.pool = LLMClientPool(max_clients=5, max_age=3600)

    def test_same_config_produces_same_key(self):
        k1 = self.pool._get_client_key("openai", "sk-test", "gpt-4")
        k2 = self.pool._get_client_key("openai", "sk-test", "gpt-4")
        assert k1 == k2

    def test_different_provider_produces_different_key(self):
        k1 = self.pool._get_client_key("openai", "sk-test", "gpt-4")
        k2 = self.pool._get_client_key("anthropic", "sk-test", "gpt-4")
        assert k1 != k2

    def test_different_model_produces_different_key(self):
        k1 = self.pool._get_client_key("openai", "sk-test", "gpt-4")
        k2 = self.pool._get_client_key("openai", "sk-test", "gpt-3.5-turbo")
        assert k1 != k2

    def test_different_api_base_produces_different_key(self):
        k1 = self.pool._get_client_key("openai", "sk-test", "gpt-4", None)
        k2 = self.pool._get_client_key("openai", "sk-test", "gpt-4", "https://custom.example.com")
        assert k1 != k2

    def test_no_api_key_handled(self):
        k = self.pool._get_client_key("openai", "", "gpt-4")
        assert isinstance(k, str)


@pytest.mark.unit
class TestLLMClientPoolCaching:
    def setup_method(self):
        self.pool = LLMClientPool(max_clients=5, max_age=3600)

    def _make_fake_client(self):
        return MagicMock()

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_cache_miss_creates_client(self, mock_config_cls, mock_client_cls):
        fake = self._make_fake_client()
        mock_client_cls.return_value = fake

        result = self.pool.get_client("openai", "sk-test", "gpt-4")

        assert result is fake
        assert self.pool.get_stats()["misses"] == 1
        assert self.pool.get_stats()["hits"] == 0

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_cache_hit_returns_same_client(self, mock_config_cls, mock_client_cls):
        fake = self._make_fake_client()
        mock_client_cls.return_value = fake

        first = self.pool.get_client("openai", "sk-test", "gpt-4")
        second = self.pool.get_client("openai", "sk-test", "gpt-4")

        assert first is second
        assert self.pool.get_stats()["hits"] == 1
        assert self.pool.get_stats()["misses"] == 1

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_stale_client_recreated(self, mock_config_cls, mock_client_cls):
        old = MagicMock()
        new = MagicMock()
        mock_client_cls.side_effect = [old, new]

        # Force small max_age so the entry becomes stale
        self.pool.max_age = 0

        first = self.pool.get_client("openai", "sk-test", "gpt-4")
        time.sleep(0.01)
        second = self.pool.get_client("openai", "sk-test", "gpt-4")

        assert first is old
        assert second is new
        assert self.pool.get_stats()["misses"] == 2

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_clear_empties_pool(self, mock_config_cls, mock_client_cls):
        mock_client_cls.return_value = MagicMock()

        self.pool.get_client("openai", "sk-test", "gpt-4")
        assert self.pool.get_stats()["active_clients"] == 1

        self.pool.clear()
        assert self.pool.get_stats()["active_clients"] == 0


@pytest.mark.unit
class TestLLMClientPoolEviction:
    def setup_method(self):
        self.pool = LLMClientPool(max_clients=2, max_age=3600)

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_lru_eviction_when_pool_full(self, mock_config_cls, mock_client_cls):
        mock_client_cls.side_effect = [MagicMock(), MagicMock(), MagicMock()]

        self.pool.get_client("openai", "sk-1", "gpt-4")
        time.sleep(0.01)
        self.pool.get_client("openai", "sk-2", "gpt-4")
        time.sleep(0.01)
        # This should evict the least-recently-used (sk-1)
        self.pool.get_client("openai", "sk-3", "gpt-4")

        assert self.pool.get_stats()["active_clients"] == 2
        assert self.pool.get_stats()["evictions"] >= 1

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_stale_cleanup_increments_evictions(self, mock_config_cls, mock_client_cls):
        mock_client_cls.side_effect = [MagicMock(), MagicMock()]

        self.pool.max_age = 0  # everything expires immediately
        self.pool.get_client("openai", "sk-1", "gpt-4")
        time.sleep(0.01)
        # Trigger cleanup by requesting another client
        self.pool.get_client("openai", "sk-2", "gpt-4")

        assert self.pool.get_stats()["evictions"] >= 1


@pytest.mark.unit
class TestLLMClientPoolStats:
    def test_initial_stats(self):
        pool = LLMClientPool()
        stats = pool.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["active_clients"] == 0
        assert stats["max_clients"] == LLMClientPool.DEFAULT_MAX_CLIENTS

    @patch("src.services.agents.llm_client.MultiProviderLLMClient")
    @patch("src.services.agents.config.ModelConfig")
    def test_stats_reflect_activity(self, mock_config_cls, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        pool = LLMClientPool()

        pool.get_client("openai", "sk-x", "gpt-4")
        pool.get_client("openai", "sk-x", "gpt-4")  # hit

        stats = pool.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1
        assert stats["active_clients"] == 1


@pytest.mark.unit
class TestGlobalPoolFunctions:
    def test_get_llm_client_pool_returns_singleton(self):
        import src.services.performance.llm_client_pool as mod

        # Reset global first
        mod._llm_client_pool = None

        from src.services.performance.llm_client_pool import get_llm_client_pool

        p1 = get_llm_client_pool()
        p2 = get_llm_client_pool()
        assert p1 is p2

    def test_close_llm_client_pool_resets_singleton(self):
        import src.services.performance.llm_client_pool as mod

        mod._llm_client_pool = None

        from src.services.performance.llm_client_pool import close_llm_client_pool, get_llm_client_pool

        get_llm_client_pool()
        close_llm_client_pool()
        assert mod._llm_client_pool is None
