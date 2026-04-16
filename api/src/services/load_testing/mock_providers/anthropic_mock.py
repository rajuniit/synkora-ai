"""
Anthropic Mock Provider

Generates mock responses in Anthropic API format.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from .base import BaseMockProvider


class AnthropicMockProvider(BaseMockProvider):
    """
    Mock provider for Anthropic API responses.

    Generates responses matching the Anthropic Messages API format.
    """

    async def generate_response(self, request_body: dict) -> dict:
        """
        Generate a non-streaming mock response.

        Args:
            request_body: The incoming request body

        Returns:
            dict: Mock response in Anthropic format
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            raise error

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        model = self._validate_model(request_body.get("model", "claude-3-sonnet-20240229"))
        messages = request_body.get("messages", [])

        # Generate response
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)

        # Estimate token usage
        input_tokens = self._estimate_input_tokens(messages)
        output_tokens = num_tokens

        # Build response
        response_id = f"msg_{uuid.uuid4().hex[:24]}"

        return {
            "id": response_id,
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": content,
                }
            ],
            "model": model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        }

    async def generate_stream(self, request_body: dict) -> AsyncGenerator[str, None]:
        """
        Generate a streaming mock response.

        Args:
            request_body: The incoming request body

        Yields:
            str: SSE-formatted response chunks in Anthropic format
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            error_event = {
                "type": "error",
                "error": {
                    "type": error.error_type,
                    "message": error.message,
                },
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
            return

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        model = self._validate_model(request_body.get("model", "claude-3-sonnet-20240229"))
        messages = request_body.get("messages", [])

        # Generate response ID
        response_id = f"msg_{uuid.uuid4().hex[:24]}"

        # Estimate input tokens
        input_tokens = self._estimate_input_tokens(messages)

        # Generate content
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)

        # Send message_start event
        message_start = {
            "type": "message_start",
            "message": {
                "id": response_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": 0,
                },
            },
        }
        yield f"event: message_start\ndata: {json.dumps(message_start)}\n\n"

        # Send content_block_start event
        content_block_start = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "text",
                "text": "",
            },
        }
        yield f"event: content_block_start\ndata: {json.dumps(content_block_start)}\n\n"

        # Stream content deltas
        words = content.split()
        for i, word in enumerate(words):
            delta = {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": word + (" " if i < len(words) - 1 else ""),
                },
            }
            yield f"event: content_block_delta\ndata: {json.dumps(delta)}\n\n"

            # Inter-token delay
            await asyncio.sleep(self._get_inter_token_delay())

        # Send content_block_stop event
        content_block_stop = {
            "type": "content_block_stop",
            "index": 0,
        }
        yield f"event: content_block_stop\ndata: {json.dumps(content_block_stop)}\n\n"

        # Send message_delta event (with stop reason and final usage)
        message_delta = {
            "type": "message_delta",
            "delta": {
                "stop_reason": "end_turn",
                "stop_sequence": None,
            },
            "usage": {
                "output_tokens": num_tokens,
            },
        }
        yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n"

        # Send message_stop event
        message_stop = {
            "type": "message_stop",
        }
        yield f"event: message_stop\ndata: {json.dumps(message_stop)}\n\n"
