"""
Safe Expression Evaluator.

Provides a secure alternative to eval() for evaluating simple conditions
in workflow configurations. This prevents arbitrary code execution.

SECURITY: This module deliberately restricts what can be evaluated:
- Only comparison operators (==, !=, <, >, <=, >=)
- Only logical operators (and, or, not)
- Only literal values (strings, numbers, booleans, None)
- Only state variable access via dot notation (state.key)
- No function calls, no imports, no attribute access beyond state

Examples of allowed conditions:
- "state.status == 'completed'"
- "state.count > 0 and state.error == None"
- "state.review_status != 'needs_revision'"
- "not state.has_error"

Examples of BLOCKED conditions (will fail safely):
- "__import__('os').system('rm -rf /')"
- "open('/etc/passwd').read()"
- "[x for x in ().__class__.__bases__[0].__subclasses__()]"
"""

import ast
import logging
import operator
from typing import Any

logger = logging.getLogger(__name__)

# Allowed comparison operators
COMPARISON_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

# Allowed boolean operators
BOOL_OPS = {
    ast.And: lambda values: all(values),
    ast.Or: lambda values: any(values),
}

# Allowed unary operators
UNARY_OPS = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class SafeEvalError(Exception):
    """Raised when safe evaluation fails or encounters disallowed operations."""

    pass


class SafeConditionEvaluator:
    """
    Safely evaluate simple conditions against a state dictionary.

    This class parses and evaluates condition strings in a restricted manner,
    preventing arbitrary code execution while allowing useful state checks.
    """

    def __init__(self, state: dict[str, Any]):
        """
        Initialize the evaluator with state context.

        Args:
            state: Dictionary of state variables accessible via state.key
        """
        self.state = state
        self.allowed_names = {"state", "True", "False", "None", "true", "false", "null"}

    def evaluate(self, condition: str) -> bool:
        """
        Safely evaluate a condition string.

        Args:
            condition: The condition to evaluate (e.g., "state.count > 0")

        Returns:
            Boolean result of the condition

        Raises:
            SafeEvalError: If the condition contains disallowed operations
        """
        if not condition or not condition.strip():
            return True

        try:
            # Parse the condition into an AST
            tree = ast.parse(condition, mode="eval")

            # Evaluate the AST safely
            result = self._eval_node(tree.body)
            return bool(result)

        except SafeEvalError:
            raise
        except SyntaxError as e:
            logger.warning(f"Syntax error in condition '{condition}': {e}")
            raise SafeEvalError(f"Invalid condition syntax: {e}")
        except Exception as e:
            logger.warning(f"Error evaluating condition '{condition}': {e}")
            raise SafeEvalError(f"Condition evaluation failed: {e}")

    def _eval_node(self, node: ast.AST) -> Any:
        """
        Recursively evaluate an AST node.

        Args:
            node: The AST node to evaluate

        Returns:
            The evaluated value

        Raises:
            SafeEvalError: If the node type is not allowed
        """
        # Constants (strings, numbers, None, True, False)
        if isinstance(node, ast.Constant):
            return node.value

        # Name (variable reference)
        if isinstance(node, ast.Name):
            if node.id not in self.allowed_names:
                raise SafeEvalError(f"Name '{node.id}' is not allowed")
            if node.id == "state":
                return self.state
            if node.id in ("True", "true"):
                return True
            if node.id in ("False", "false"):
                return False
            if node.id in ("None", "null"):
                return None
            raise SafeEvalError(f"Name '{node.id}' is not allowed")

        # Attribute access (only state.xxx allowed)
        if isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            if not isinstance(value, dict):
                raise SafeEvalError("Attribute access only allowed on state dictionary")
            return value.get(node.attr)

        # Subscript access (state["key"] or state[0])
        if isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            if not isinstance(value, (dict, list)):
                raise SafeEvalError("Subscript access only allowed on dict/list")
            key = self._eval_node(node.slice)
            try:
                return value[key]
            except (KeyError, IndexError, TypeError):
                return None

        # Comparison operations
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                op_func = COMPARISON_OPS.get(type(op))
                if op_func is None:
                    raise SafeEvalError(f"Comparison operator {type(op).__name__} is not allowed")
                right = self._eval_node(comparator)
                try:
                    if not op_func(left, right):
                        return False
                except TypeError:
                    # Handle comparison errors (e.g., comparing None with int)
                    return False
                left = right
            return True

        # Boolean operations (and, or)
        if isinstance(node, ast.BoolOp):
            op_func = BOOL_OPS.get(type(node.op))
            if op_func is None:
                raise SafeEvalError(f"Boolean operator {type(node.op).__name__} is not allowed")
            values = [self._eval_node(v) for v in node.values]
            return op_func(values)

        # Unary operations (not, -)
        if isinstance(node, ast.UnaryOp):
            op_func = UNARY_OPS.get(type(node.op))
            if op_func is None:
                raise SafeEvalError(f"Unary operator {type(node.op).__name__} is not allowed")
            operand = self._eval_node(node.operand)
            return op_func(operand)

        # List literal
        if isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        # Tuple literal
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elem) for elem in node.elts)

        # Dict literal
        if isinstance(node, ast.Dict):
            keys = [self._eval_node(k) if k is not None else None for k in node.keys]
            values = [self._eval_node(v) for v in node.values]
            return dict(zip(keys, values, strict=False))

        # Reject everything else (function calls, imports, etc.)
        raise SafeEvalError(
            f"Operation type '{type(node).__name__}' is not allowed in conditions. "
            "Only comparisons, boolean operators, and state access are permitted."
        )


def safe_eval_condition(condition: str, state: dict[str, Any]) -> bool:
    """
    Safely evaluate a condition string against a state dictionary.

    This is a convenience function that creates a SafeConditionEvaluator
    and evaluates the condition.

    Args:
        condition: The condition to evaluate
        state: The state dictionary

    Returns:
        Boolean result of the condition, or False if evaluation fails
    """
    if not condition:
        return True

    try:
        evaluator = SafeConditionEvaluator(state)
        return evaluator.evaluate(condition)
    except SafeEvalError as e:
        logger.warning(f"Safe eval rejected condition: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in safe eval: {e}")
        return False
