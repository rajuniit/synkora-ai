"""
Unit tests for llm_cost_service.

Tests pricing resolution, cost calculation, and fire_persist_llm_usage.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


class TestResolvePricing:
    def test_db_override_wins(self):
        from src.services.billing.llm_cost_service import _resolve_pricing

        routing_rules = {"cost_per_1k_input": 0.999, "cost_per_1k_output": 1.999}
        inp, out = _resolve_pricing("gpt-4o", routing_rules)
        assert inp == 0.999
        assert out == 1.999

    def test_builtin_costs_fallback(self):
        from src.services.billing.llm_cost_service import _resolve_pricing

        inp, out = _resolve_pricing("gpt-4o", None)
        assert inp is not None
        assert inp > 0

    def test_unknown_model_returns_none(self):
        from src.services.billing.llm_cost_service import _resolve_pricing

        inp, out = _resolve_pricing("totally-unknown-model-xyz-12345", None)
        assert inp is None
        assert out is None

    def test_anthropic_model_resolves(self):
        from src.services.billing.llm_cost_service import _resolve_pricing

        inp, out = _resolve_pricing("claude-haiku-4-5-20251001", None)
        assert inp is not None
        assert inp > 0


class TestCalculateCost:
    def test_basic_cost(self):
        from src.services.billing.llm_cost_service import calculate_cost

        cost = calculate_cost("gpt-4o-mini", 1000, 500)
        assert cost is not None
        assert cost > 0

    def test_anthropic_cache_cost(self):
        from src.services.billing.llm_cost_service import calculate_cost

        # cache_read at 10% of input rate, cache_creation at 125%
        model = "claude-haiku-4-5-20251001"
        cost_no_cache = calculate_cost(model, 1000, 100)
        cost_with_read = calculate_cost(model, 1000, 100, cache_read_tokens=500)
        cost_with_create = calculate_cost(model, 1000, 100, cache_creation_tokens=500)

        # cache_read should be cheaper than full-rate input
        assert cost_with_read < cost_no_cache
        # cache_creation should be more expensive than full-rate input
        assert cost_with_create > cost_no_cache

    def test_unknown_model_returns_none(self):
        from src.services.billing.llm_cost_service import calculate_cost

        cost = calculate_cost("totally-unknown-model-xyz", 1000, 500)
        assert cost is None

    def test_db_override_pricing(self):
        from src.services.billing.llm_cost_service import calculate_cost

        routing_rules = {"cost_per_1k_input": 0.001, "cost_per_1k_output": 0.002}
        cost = calculate_cost("gpt-4o", 1000, 1000, routing_rules=routing_rules)
        assert cost is not None
        # 1000 input * 0.001/1k + 1000 output * 0.002/1k = 0.001 + 0.002 = 0.003
        assert abs(cost - 0.003) < 1e-7


class TestFirePersistLLMUsage:
    def test_fire_persist_never_raises(self):
        """fire_persist_llm_usage must never propagate exceptions."""
        from src.services.billing.llm_cost_service import fire_persist_llm_usage

        with patch("src.services.billing.llm_cost_service._persist_llm_usage", side_effect=RuntimeError("db down")):
            with patch("asyncio.create_task", side_effect=RuntimeError("no event loop")):
                # Must not raise
                fire_persist_llm_usage(
                    tenant_id=TENANT_ID,
                    provider="openai",
                    model_name="gpt-4o-mini",
                    input_tokens=100,
                    output_tokens=50,
                )

    def test_creates_background_task(self):
        """fire_persist_llm_usage schedules an asyncio task."""
        from src.services.billing.llm_cost_service import fire_persist_llm_usage

        mock_task = MagicMock()
        mock_task.add_done_callback = MagicMock()

        with patch("asyncio.create_task", return_value=mock_task) as mock_create:
            fire_persist_llm_usage(
                tenant_id=TENANT_ID,
                provider="anthropic",
                model_name="claude-haiku-4-5-20251001",
                input_tokens=200,
                output_tokens=100,
            )
            mock_create.assert_called_once()
            mock_task.add_done_callback.assert_called_once()
