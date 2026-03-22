"""Pytest configuration for workflow tests."""

import sys

# Only install a mock if the real module can't be imported
# This prevents breaking tests for the actual safe_eval module
try:
    from src.services.security.safe_eval import safe_eval_condition  # noqa: F401
except ImportError:
    # Fall back to a mock implementation if the real module is unavailable
    def _safe_eval_condition(condition: str, state: dict) -> bool:
        """Test implementation of safe_eval_condition."""
        try:
            return eval(
                condition,
                {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "bool": bool}},
                {"state": state},
            )
        except Exception:
            return False

    # Mock the security module before any workflow imports
    _mock_safe_eval_module = type(sys)("src.services.security.safe_eval")
    _mock_safe_eval_module.safe_eval_condition = _safe_eval_condition

    # Ensure the parent package exists
    if "src.services.security" not in sys.modules:
        _mock_security_pkg = type(sys)("src.services.security")
        _mock_security_pkg.__path__ = []
        sys.modules["src.services.security"] = _mock_security_pkg

    # Install the safe_eval mock
    sys.modules["src.services.security.safe_eval"] = _mock_safe_eval_module
