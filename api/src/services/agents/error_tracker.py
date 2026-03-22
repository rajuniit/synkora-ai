"""
Circuit Breaker for Function Calling Errors.

Detects repeated errors (especially parameter validation errors) and stops
the function calling loop to prevent infinite loops from stubborn LLMs.
"""

import logging

logger = logging.getLogger(__name__)


class FunctionCallingErrorTracker:
    """
    Tracks function calling errors and implements circuit breaker logic.

    Prevents infinite loops when LLMs repeatedly call tools with the same errors.
    """

    def __init__(self, max_repeated_errors: int = 3):
        """
        Initialize error tracker.

        Args:
            max_repeated_errors: Number of times same error can repeat before circuit breaks
        """
        self.max_repeated_errors = max_repeated_errors
        self.error_counts: dict[str, int] = {}

    def track_error(self, tool_name: str, error_message: str) -> bool:
        """
        Track an error occurrence.

        Args:
            tool_name: Name of the tool that failed
            error_message: The error message

        Returns:
            True if circuit should break (error repeated too many times), False otherwise
        """
        # Track per (tool + error signature) so that:
        # - The same URL failing 3 times breaks the circuit
        # - Different URLs each failing once do NOT break the circuit
        # This allows agents fetching multiple URLs to handle some 404s gracefully.
        error_key = f"{tool_name}:{error_message[:100]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        if self.error_counts[error_key] >= self.max_repeated_errors:
            logger.error(
                f"🚨 CIRCUIT BREAKER: Tool '{tool_name}' failed {self.error_counts[error_key]} "
                f"times with the same error. Last error: {error_message[:200]}. Stopping to prevent infinite loop."
            )
            return True

        return False

    def get_error_summary(self) -> dict[str, int]:
        """Get summary of all tracked errors."""
        return self.error_counts.copy()

    def reset(self):
        """Reset all error tracking."""
        self.error_counts.clear()
