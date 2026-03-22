"""
Unit tests for Safe Eval module.

Tests safe condition evaluation and protection against code injection.
"""

import pytest

from src.services.security.safe_eval import (
    SafeConditionEvaluator,
    SafeEvalError,
    safe_eval_condition,
)


class TestSafeConditionEvaluator:
    """Test SafeConditionEvaluator class."""

    @pytest.fixture
    def state(self):
        """Sample state dictionary for testing."""
        return {
            "status": "completed",
            "count": 10,
            "error": None,
            "has_error": False,
            "items": ["a", "b", "c"],
            "config": {"enabled": True},
            "score": 85.5,
        }

    def test_init(self, state):
        """Test evaluator initialization."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.state == state

    def test_empty_condition_returns_true(self, state):
        """Test that empty condition returns True."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("") is True
        assert evaluator.evaluate("   ") is True

    def test_simple_equality(self, state):
        """Test simple equality comparison."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.status == 'completed'") is True
        assert evaluator.evaluate("state.status == 'pending'") is False

    def test_numeric_comparisons(self, state):
        """Test numeric comparisons."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.count > 5") is True
        assert evaluator.evaluate("state.count < 5") is False
        assert evaluator.evaluate("state.count >= 10") is True
        assert evaluator.evaluate("state.count <= 10") is True
        assert evaluator.evaluate("state.count != 5") is True

    def test_none_comparison(self, state):
        """Test None comparison."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.error == None") is True
        assert evaluator.evaluate("state.error is None") is True
        assert evaluator.evaluate("state.status is not None") is True

    def test_boolean_state(self, state):
        """Test boolean state values."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.has_error == False") is True
        assert evaluator.evaluate("state.has_error == True") is False

    def test_not_operator(self, state):
        """Test not operator."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("not state.has_error") is True
        assert evaluator.evaluate("not state.config") is False

    def test_and_operator(self, state):
        """Test and operator."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.count > 0 and state.status == 'completed'") is True
        assert evaluator.evaluate("state.count > 0 and state.status == 'pending'") is False

    def test_or_operator(self, state):
        """Test or operator."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.count < 0 or state.status == 'completed'") is True
        assert evaluator.evaluate("state.count < 0 or state.status == 'pending'") is False

    def test_nested_dict_access(self, state):
        """Test nested dictionary access."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.config.enabled == True") is True

    def test_list_access(self, state):
        """Test list access."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.items[0] == 'a'") is True

    def test_in_operator(self, state):
        """Test in operator."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("'a' in state.items") is True
        assert evaluator.evaluate("'z' not in state.items") is True

    def test_missing_key_returns_none(self, state):
        """Test that missing key returns None."""
        evaluator = SafeConditionEvaluator(state)
        assert evaluator.evaluate("state.nonexistent == None") is True


class TestSafeEvalSecurity:
    """Test security protections."""

    @pytest.fixture
    def state(self):
        """Sample state for testing."""
        return {"status": "ok"}

    def test_rejects_function_calls(self, state):
        """Test that function calls are rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("len(state.status)")

    def test_rejects_import(self, state):
        """Test that imports are rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("__import__('os')")

    def test_rejects_arbitrary_names(self, state):
        """Test that arbitrary names are rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("os.system('ls')")

    def test_rejects_class_access(self, state):
        """Test that class access is rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("().__class__.__bases__")

    def test_rejects_lambda(self, state):
        """Test that lambda is rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("(lambda: 1)()")

    def test_rejects_comprehension(self, state):
        """Test that comprehensions are rejected."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("[x for x in [1,2,3]]")

    def test_invalid_syntax_raises_error(self, state):
        """Test that invalid syntax raises SafeEvalError."""
        evaluator = SafeConditionEvaluator(state)
        with pytest.raises(SafeEvalError):
            evaluator.evaluate("state.status ==")


class TestSafeEvalConditionFunction:
    """Test the safe_eval_condition convenience function."""

    def test_successful_evaluation(self):
        """Test successful condition evaluation."""
        state = {"count": 5}
        assert safe_eval_condition("state.count > 0", state) is True
        assert safe_eval_condition("state.count < 0", state) is False

    def test_empty_condition_returns_true(self):
        """Test empty condition returns True."""
        assert safe_eval_condition("", {}) is True
        assert safe_eval_condition(None, {}) is True

    def test_invalid_condition_returns_false(self):
        """Test that invalid conditions return False (not raise)."""
        state = {"status": "ok"}
        # Function calls should return False, not raise
        assert safe_eval_condition("len(state.status)", state) is False

    def test_syntax_error_returns_false(self):
        """Test that syntax errors return False."""
        state = {"status": "ok"}
        assert safe_eval_condition("state.status ==", state) is False


class TestSafeEvalError:
    """Test SafeEvalError exception."""

    def test_exception_message(self):
        """Test exception can be raised with message."""
        with pytest.raises(SafeEvalError) as exc_info:
            raise SafeEvalError("Test error message")
        assert "Test error message" in str(exc_info.value)

    def test_is_exception_subclass(self):
        """Test SafeEvalError is an Exception subclass."""
        assert issubclass(SafeEvalError, Exception)
