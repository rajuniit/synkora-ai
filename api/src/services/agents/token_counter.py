"""
Token Counter Service.

Accurate token counting using tiktoken with model-aware encoding.
Provides consistent token counting across all agent services.
"""

import logging
from functools import lru_cache
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)


class TokenCounter:
    """Accurate token counting using tiktoken with model-aware encoding."""

    # Model to encoding mapping
    # See: https://github.com/openai/tiktoken/blob/main/tiktoken/model.py
    MODEL_ENCODINGS = {
        # OpenAI models
        "gpt-4": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4-turbo-preview": "cl100k_base",
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-3.5-turbo-16k": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        # Claude models (approximate with cl100k_base)
        "claude-opus-4-6": "cl100k_base",
        "claude-sonnet-4-6": "cl100k_base",
        "claude-opus-4-5": "cl100k_base",
        "claude-sonnet-4-5": "cl100k_base",
        "claude-haiku-4-5": "cl100k_base",
        "claude-opus-4": "cl100k_base",
        "claude-sonnet-4": "cl100k_base",
        "claude-3-opus": "cl100k_base",
        "claude-3-sonnet": "cl100k_base",
        "claude-3-haiku": "cl100k_base",
        "claude-3.5-sonnet": "cl100k_base",
        "claude-2": "cl100k_base",
        "claude": "cl100k_base",
        # Gemini models (approximate with cl100k_base)
        "gemini-pro": "cl100k_base",
        "gemini-1.5-pro": "cl100k_base",
        "gemini-1.5-flash": "cl100k_base",
        "gemini": "cl100k_base",
        "default": "cl100k_base",
    }

    # Token overhead for message formatting (per message)
    # This accounts for special tokens like role markers
    MESSAGE_TOKEN_OVERHEAD = 4  # <role>, </role>, newlines etc.

    # Per-conversation overhead for system prompt
    SYSTEM_PROMPT_OVERHEAD = 3

    @classmethod
    @lru_cache(maxsize=10)
    def get_encoding(cls, model: str) -> tiktoken.Encoding:
        """
        Get encoding for model with caching.

        Args:
            model: Model name or identifier

        Returns:
            tiktoken Encoding object
        """
        # Normalize model name (lowercase, remove version suffixes)
        normalized = model.lower().split("-20")[0]  # Remove date suffixes

        # Find matching encoding
        encoding_name = None
        for model_prefix, enc_name in cls.MODEL_ENCODINGS.items():
            if normalized.startswith(model_prefix) or model_prefix in normalized:
                encoding_name = enc_name
                break

        if not encoding_name:
            encoding_name = cls.MODEL_ENCODINGS["default"]
            logger.debug(f"Using default encoding for unknown model: {model}")

        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to get encoding {encoding_name}: {e}, using cl100k_base")
            return tiktoken.get_encoding("cl100k_base")

    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens accurately using tiktoken.

        Args:
            text: Text to count tokens for
            model: Model name for encoding selection

        Returns:
            Token count
        """
        if not text:
            return 0

        try:
            encoding = cls.get_encoding(model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using fallback: {e}")
            return cls._fallback_estimate(text)

    @classmethod
    def count_messages_tokens(
        cls, messages: list[dict[str, Any]], model: str = "gpt-4", include_overhead: bool = True
    ) -> int:
        """
        Count tokens for message list including overhead.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name for encoding selection
            include_overhead: Whether to include message format overhead

        Returns:
            Total token count for all messages
        """
        if not messages:
            return 0

        total_tokens = 0
        encoding = cls.get_encoding(model)

        for message in messages:
            # Count content tokens
            content = message.get("content", "")
            if content:
                try:
                    total_tokens += len(encoding.encode(content))
                except Exception:
                    total_tokens += cls._fallback_estimate(content)

            # Count role tokens
            role = message.get("role", "")
            if role:
                try:
                    total_tokens += len(encoding.encode(role))
                except Exception:
                    total_tokens += cls._fallback_estimate(role)

            # Add message overhead
            if include_overhead:
                total_tokens += cls.MESSAGE_TOKEN_OVERHEAD

        return total_tokens

    @classmethod
    def count_prompt_tokens(cls, prompt: str, system_prompt: str | None = None, model: str = "gpt-4") -> int:
        """
        Count tokens for a full prompt including system prompt.

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt
            model: Model name for encoding selection

        Returns:
            Total token count
        """
        total = cls.count_tokens(prompt, model)

        if system_prompt:
            total += cls.count_tokens(system_prompt, model)
            total += cls.SYSTEM_PROMPT_OVERHEAD

        return total

    @classmethod
    def estimate_response_budget(cls, input_tokens: int, max_context_tokens: int, reserve_ratio: float = 0.2) -> int:
        """
        Estimate available tokens for response given input tokens.

        Args:
            input_tokens: Number of input tokens
            max_context_tokens: Maximum context window size
            reserve_ratio: Ratio of max tokens to reserve for response (0.0-1.0)

        Returns:
            Estimated available tokens for response
        """
        reserved = int(max_context_tokens * reserve_ratio)
        available = max_context_tokens - input_tokens - reserved
        return max(0, available)

    @classmethod
    def _fallback_estimate(cls, text: str) -> int:
        """
        Fallback estimation when tiktoken fails.

        Uses ~4 characters per token as rough approximation.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    @classmethod
    def truncate_to_tokens(cls, text: str, max_tokens: int, model: str = "gpt-4", suffix: str = "...") -> str:
        """
        Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            model: Model name for encoding selection
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if not text:
            return text

        current_tokens = cls.count_tokens(text, model)
        if current_tokens <= max_tokens:
            return text

        encoding = cls.get_encoding(model)
        suffix_tokens = len(encoding.encode(suffix)) if suffix else 0
        target_tokens = max_tokens - suffix_tokens

        try:
            tokens = encoding.encode(text)
            truncated_tokens = tokens[:target_tokens]
            truncated_text = encoding.decode(truncated_tokens)
            return truncated_text + suffix
        except Exception as e:
            logger.warning(f"Token truncation failed, using char estimate: {e}")
            char_limit = max_tokens * 4
            return text[:char_limit] + suffix


# Convenience function for backward compatibility
def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text.

    This is a convenience wrapper around TokenCounter.count_tokens().

    Args:
        text: Text to count tokens for
        model: Model name for encoding selection

    Returns:
        Token count
    """
    return TokenCounter.count_tokens(text, model)


def count_messages_tokens(messages: list[dict[str, Any]], model: str = "gpt-4") -> int:
    """
    Count tokens for a list of messages.

    This is a convenience wrapper around TokenCounter.count_messages_tokens().

    Args:
        messages: List of message dicts
        model: Model name for encoding selection

    Returns:
        Total token count
    """
    return TokenCounter.count_messages_tokens(messages, model)
