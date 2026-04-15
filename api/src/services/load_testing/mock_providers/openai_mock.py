"""
OpenAI Mock Provider

Generates mock responses in OpenAI API format.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator

from .base import BaseMockProvider


class OpenAIMockProvider(BaseMockProvider):
    """
    Mock provider for OpenAI-compatible API responses.

    Generates responses matching the OpenAI Chat Completions API format.
    """

    async def generate_response(self, request_body: dict) -> dict:
        """
        Generate a non-streaming mock response.

        Args:
            request_body: The incoming request body

        Returns:
            dict: Mock response in OpenAI format
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            raise error

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        model = self._validate_model(request_body.get("model", "gpt-4-turbo"))
        messages = request_body.get("messages", [])

        # Generate response
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)

        # Estimate token usage
        prompt_tokens = self._estimate_input_tokens(messages)
        completion_tokens = num_tokens
        total_tokens = prompt_tokens + completion_tokens

        # Build response
        response_id = self._generate_id()
        created = int(time.time())

        return {
            "id": response_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "system_fingerprint": f"fp_mock_{response_id[-8:]}",
        }

    async def generate_stream(self, request_body: dict) -> AsyncGenerator[str, None]:
        """
        Generate a streaming mock response.

        Args:
            request_body: The incoming request body

        Yields:
            str: SSE-formatted response chunks
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            error_response = {
                "error": {
                    "type": error.error_type,
                    "message": error.message,
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
            return

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        model = self._validate_model(request_body.get("model", "gpt-4-turbo"))

        # Generate response ID
        response_id = self._generate_id()
        created = int(time.time())

        # Generate content
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)

        # Split content into tokens (words for simulation)
        words = content.split()

        # Stream chunks
        for i, word in enumerate(words):
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": word + (" " if i < len(words) - 1 else ""),
                        },
                        "logprobs": None,
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

            # Inter-token delay
            await asyncio.sleep(self._get_inter_token_delay())

        # Send final chunk with finish_reason
        final_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def get_models_list(self) -> dict:
        """
        Generate a mock models list response.

        Returns:
            dict: Mock models list in OpenAI format
        """
        allowed_models = self.models_config.get("allowed", ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])

        models = []
        for model_name in allowed_models:
            models.append(
                {
                    "id": model_name,
                    "object": "model",
                    "created": 1686935002,
                    "owned_by": "synkora-mock",
                }
            )

        return {
            "object": "list",
            "data": models,
        }
