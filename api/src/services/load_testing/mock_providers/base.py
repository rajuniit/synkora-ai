"""
Base Mock Provider

Abstract base class for mock LLM providers.
"""

import random
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

# Lorem ipsum words for generating mock responses
LOREM_WORDS = [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua",
    "enim",
    "ad",
    "minim",
    "veniam",
    "quis",
    "nostrud",
    "exercitation",
    "ullamco",
    "laboris",
    "nisi",
    "aliquip",
    "ex",
    "ea",
    "commodo",
    "consequat",
    "duis",
    "aute",
    "irure",
    "in",
    "reprehenderit",
    "voluptate",
    "velit",
    "esse",
    "cillum",
    "fugiat",
    "nulla",
    "pariatur",
    "excepteur",
    "sint",
    "occaecat",
    "cupidatat",
    "non",
    "proident",
    "sunt",
    "culpa",
    "qui",
    "officia",
    "deserunt",
    "mollit",
    "anim",
    "id",
    "est",
    "laborum",
]

# AI-like response templates
AI_TEMPLATES = [
    "I understand your question about {topic}. ",
    "That's an interesting point. ",
    "Based on my analysis, ",
    "Let me explain this concept. ",
    "Here's what I found: ",
    "The key insight here is ",
    "To answer your question, ",
    "This is a great question! ",
    "From my understanding, ",
    "Allow me to elaborate on that. ",
]


class MockError(Exception):
    """Mock error for simulating API failures."""

    def __init__(self, error_type: str, message: str, status_code: int = 500):
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BaseMockProvider(ABC):
    """
    Abstract base class for mock LLM providers.

    Provides common functionality for generating mock responses
    with configurable latency and error simulation.
    """

    def __init__(self, mock_config: dict):
        """
        Initialize the mock provider.

        Args:
            mock_config: Configuration dictionary with latency, response, and error settings
        """
        self.config = mock_config
        self.latency_config = mock_config.get("latency", {})
        self.response_config = mock_config.get("response", {})
        self.error_config = mock_config.get("errors", {})
        self.models_config = mock_config.get("models", {})

    def _should_error(self) -> bool:
        """Check if this request should return an error."""
        error_rate = self.error_config.get("rate", 0.01)
        return random.random() < error_rate

    def _get_error(self) -> MockError:
        """Generate a random error based on configuration."""
        error_types = self.error_config.get("types", ["rate_limit", "timeout"])
        error_type = random.choice(error_types)

        if error_type == "rate_limit":
            return MockError(
                error_type="rate_limit_exceeded",
                message="Rate limit exceeded. Please retry after 60 seconds.",
                status_code=429,
            )
        elif error_type == "timeout":
            return MockError(
                error_type="timeout",
                message="Request timed out.",
                status_code=504,
            )
        elif error_type == "server_error":
            return MockError(
                error_type="internal_error",
                message="Internal server error.",
                status_code=500,
            )
        elif error_type == "invalid_request":
            return MockError(
                error_type="invalid_request",
                message="Invalid request parameters.",
                status_code=400,
            )
        elif error_type == "authentication":
            return MockError(
                error_type="authentication_error",
                message="Invalid API key.",
                status_code=401,
            )
        else:
            return MockError(
                error_type="unknown_error",
                message="An unknown error occurred.",
                status_code=500,
            )

    def _get_ttft_delay(self) -> float:
        """Get time to first token delay in seconds."""
        min_ms = self.latency_config.get("ttft_min_ms", 100)
        max_ms = self.latency_config.get("ttft_max_ms", 500)
        return random.randint(min_ms, max_ms) / 1000.0

    def _get_inter_token_delay(self) -> float:
        """Get inter-token delay in seconds."""
        min_ms = self.latency_config.get("inter_token_min_ms", 10)
        max_ms = self.latency_config.get("inter_token_max_ms", 50)
        return random.randint(min_ms, max_ms) / 1000.0

    def _get_response_tokens(self) -> int:
        """Get number of tokens to generate."""
        min_tokens = self.response_config.get("min_tokens", 50)
        max_tokens = self.response_config.get("max_tokens", 500)
        return random.randint(min_tokens, max_tokens)

    def _generate_content(self, num_tokens: int) -> str:
        """
        Generate mock response content.

        Args:
            num_tokens: Approximate number of tokens to generate

        Returns:
            str: Generated content
        """
        templates = self.response_config.get("templates", [])
        use_lorem = self.response_config.get("use_lorem", True)

        if templates:
            # Use template as base
            base = random.choice(templates)
            # Replace placeholders if any
            base = base.replace("{topic}", random.choice(["this topic", "the subject", "your question"]))
        else:
            base = random.choice(AI_TEMPLATES)
            base = base.replace("{topic}", random.choice(["this topic", "the subject", "your question"]))

        # Add words to reach target token count
        # Approximate 1 token = 0.75 words
        target_words = int(num_tokens * 0.75)
        current_words = len(base.split())

        if use_lorem:
            words_needed = max(0, target_words - current_words)
            additional_words = [random.choice(LOREM_WORDS) for _ in range(words_needed)]
            content = base + " " + " ".join(additional_words)
        else:
            # Just repeat base content
            repeat_times = max(1, target_words // current_words)
            content = (base + " ") * repeat_times

        return content.strip()

    def _validate_model(self, model: str) -> str:
        """
        Validate and normalize model name.

        Args:
            model: Requested model name

        Returns:
            str: Validated model name
        """
        allowed_models = self.models_config.get("allowed", [])
        default_model = self.models_config.get("default", "gpt-4-turbo")

        if not allowed_models:
            return model or default_model

        if model in allowed_models:
            return model

        # Return default if requested model not allowed
        return default_model

    @abstractmethod
    async def generate_response(self, request_body: dict) -> dict:
        """
        Generate a non-streaming mock response.

        Args:
            request_body: The incoming request body

        Returns:
            dict: Mock response in provider-specific format
        """
        pass

    @abstractmethod
    async def generate_stream(self, request_body: dict) -> AsyncGenerator[str, None]:
        """
        Generate a streaming mock response.

        Args:
            request_body: The incoming request body

        Yields:
            str: SSE-formatted response chunks
        """
        pass

    def _estimate_input_tokens(self, messages: list) -> int:
        """Estimate input token count from messages."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        # Approximate 4 chars per token
        return total_chars // 4

    def _generate_id(self) -> str:
        """Generate a unique ID for the response."""
        import uuid

        return f"chatcmpl-{uuid.uuid4().hex[:24]}"
