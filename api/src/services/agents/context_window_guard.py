"""
Context Window Guard - Proactive context monitoring and protection.

Monitors token usage and warns/blocks before context exhaustion,
preventing failures from context overflow.

"""

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class ContextGuardAction(StrEnum):
    """Action recommended by the context guard."""

    OK = "ok"  # Proceed normally
    WARN = "warn"  # Warn but proceed
    SUMMARIZE = "summarize"  # Recommend summarization
    BLOCK = "block"  # Block execution


@dataclass
class ContextGuardResult:
    """Result of context window evaluation."""

    action: ContextGuardAction
    current_tokens: int
    max_tokens: int
    remaining_tokens: int
    remaining_percentage: float
    message: str | None = None

    @property
    def should_block(self) -> bool:
        return self.action == ContextGuardAction.BLOCK

    @property
    def should_warn(self) -> bool:
        return self.action in (ContextGuardAction.WARN, ContextGuardAction.SUMMARIZE)

    @property
    def should_summarize(self) -> bool:
        return self.action == ContextGuardAction.SUMMARIZE


# Model context limits (conservative estimates leaving room for output)
MODEL_CONTEXT_LIMITS = {
    # Anthropic Claude models (200K context window, leave room for output)
    "claude-opus-4-6": 180000,
    "claude-sonnet-4-6": 180000,
    "claude-3-opus": 180000,
    "claude-3-sonnet": 180000,
    "claude-3-haiku": 180000,
    "claude-3.5-sonnet": 180000,
    "claude-3.5-haiku": 180000,
    "claude-sonnet-4": 180000,
    "claude-opus-4": 180000,
    "claude-4-5-sonnet": 180000,
    "claude-4-sonnet": 180000,
    "claude-4-opus": 180000,
    "claude-4-5-opus": 180000,
    "claude-haiku-4": 180000,
    "claude-haiku-4-5": 180000,
    # OpenAI models
    "gpt-4": 8000,
    "gpt-4-turbo": 120000,
    "gpt-4o": 120000,
    "gpt-4o-mini": 120000,
    "gpt-4.1": 1000000,
    "gpt-4.1-mini": 1000000,
    "gpt-4.1-nano": 1000000,
    "gpt-3.5-turbo": 12000,
    "gpt-3.5-turbo-16k": 14000,
    "o3": 180000,
    "o3-mini": 180000,
    "o4-mini": 180000,
    # Google models
    "gemini-pro": 28000,
    "gemini-1.5-pro": 950000,
    "gemini-1.5-flash": 950000,
    "gemini-2.0-flash": 950000,
    "gemini-2.5-pro": 1000000,
    "gemini-2.5-flash": 1000000,
    # Default - use a reasonable fallback instead of 8K
    "default": 180000,
}


class ContextWindowGuard:
    """
    Guards against context window exhaustion.

    Evaluates current token usage against model limits and recommends
    appropriate actions to prevent context overflow.

    Usage:
        guard = ContextWindowGuard()
        result = guard.evaluate("claude-3.5-sonnet", current_tokens=150000)

        if result.should_block:
            raise ContextExhaustedError(result.message)
        elif result.should_summarize:
            # Trigger summarization
            ...
        elif result.should_warn:
            logger.warning(result.message)
    """

    # Thresholds for different actions
    WARN_THRESHOLD = 0.40  # Warn when 40% remaining
    SUMMARIZE_THRESHOLD = 0.25  # Recommend summarization at 25% remaining
    BLOCK_THRESHOLD = 1000  # Hard block at 1000 tokens remaining

    def __init__(
        self,
        warn_threshold: float = WARN_THRESHOLD,
        summarize_threshold: float = SUMMARIZE_THRESHOLD,
        block_threshold: int = BLOCK_THRESHOLD,
    ):
        """
        Initialize the context window guard.

        Args:
            warn_threshold: Percentage remaining to trigger warning (0.0-1.0)
            summarize_threshold: Percentage remaining to recommend summarization
            block_threshold: Absolute token count to trigger block
        """
        self.warn_threshold = warn_threshold
        self.summarize_threshold = summarize_threshold
        self.block_threshold = block_threshold

    def get_model_limit(self, model: str) -> int:
        """
        Get the context limit for a model.

        Args:
            model: Model name or ID

        Returns:
            Context token limit
        """
        model_lower = model.lower() if model else ""

        # Try exact match first
        if model_lower in MODEL_CONTEXT_LIMITS:
            return MODEL_CONTEXT_LIMITS[model_lower]

        # Try partial match
        for key, limit in MODEL_CONTEXT_LIMITS.items():
            if key in model_lower or model_lower in key:
                return limit

        # Default
        logger.debug(f"Unknown model '{model}', using default context limit")
        return MODEL_CONTEXT_LIMITS["default"]

    def evaluate(
        self,
        model: str,
        current_tokens: int,
        custom_limit: int | None = None,
    ) -> ContextGuardResult:
        """
        Evaluate context window status.

        Args:
            model: Model name or ID
            current_tokens: Current token count
            custom_limit: Optional custom token limit override

        Returns:
            ContextGuardResult with recommended action
        """
        max_tokens = custom_limit or self.get_model_limit(model)
        remaining = max_tokens - current_tokens
        remaining_pct = remaining / max_tokens if max_tokens > 0 else 0

        # Check block threshold (absolute)
        if remaining <= self.block_threshold:
            return ContextGuardResult(
                action=ContextGuardAction.BLOCK,
                current_tokens=current_tokens,
                max_tokens=max_tokens,
                remaining_tokens=remaining,
                remaining_percentage=remaining_pct,
                message=f"Context window exhausted: {remaining} tokens remaining "
                f"(minimum {self.block_threshold} required). "
                "Please start a new conversation or clear history.",
            )

        # Check summarize threshold
        if remaining_pct <= self.summarize_threshold:
            return ContextGuardResult(
                action=ContextGuardAction.SUMMARIZE,
                current_tokens=current_tokens,
                max_tokens=max_tokens,
                remaining_tokens=remaining,
                remaining_percentage=remaining_pct,
                message=f"Context window low: {remaining} tokens remaining "
                f"({remaining_pct:.1%}). Summarization recommended.",
            )

        # Check warn threshold
        if remaining_pct <= self.warn_threshold:
            return ContextGuardResult(
                action=ContextGuardAction.WARN,
                current_tokens=current_tokens,
                max_tokens=max_tokens,
                remaining_tokens=remaining,
                remaining_percentage=remaining_pct,
                message=f"Context window usage high: {remaining} tokens remaining ({remaining_pct:.1%}).",
            )

        # All good
        return ContextGuardResult(
            action=ContextGuardAction.OK,
            current_tokens=current_tokens,
            max_tokens=max_tokens,
            remaining_tokens=remaining,
            remaining_percentage=remaining_pct,
        )

    def estimate_tokens_for_message(
        self,
        message: str,
        role: str = "user",
    ) -> int:
        """
        Estimate token count for a message.

        This is a rough estimate. For accurate counts, use tiktoken.

        Args:
            message: Message content
            role: Message role (user, assistant, system)

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token on average
        # Add overhead for message structure
        base_tokens = len(message) // 4
        overhead = 4  # For role and message structure

        return base_tokens + overhead

    def can_add_message(
        self,
        model: str,
        current_tokens: int,
        new_message: str,
        expected_response_tokens: int = 4000,
    ) -> tuple[bool, ContextGuardResult]:
        """
        Check if a new message can be added without exhausting context.

        Args:
            model: Model name or ID
            current_tokens: Current token count
            new_message: Message to add
            expected_response_tokens: Expected response size

        Returns:
            Tuple of (can_add, result)
        """
        message_tokens = self.estimate_tokens_for_message(new_message)
        total_tokens = current_tokens + message_tokens + expected_response_tokens

        result = self.evaluate(model, total_tokens)

        can_add = result.action != ContextGuardAction.BLOCK
        return can_add, result


class ContextExhaustedError(Exception):
    """Raised when context window is exhausted."""

    def __init__(self, message: str, result: ContextGuardResult | None = None):
        super().__init__(message)
        self.result = result


# Global instance for easy access
_guard_instance: ContextWindowGuard | None = None


def get_context_guard() -> ContextWindowGuard:
    """Get the global ContextWindowGuard instance."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = ContextWindowGuard()
    return _guard_instance
