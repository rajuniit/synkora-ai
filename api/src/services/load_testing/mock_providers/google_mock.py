"""
Google Mock Provider

Generates mock responses in Google Generative AI API format.
"""

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator

from .base import BaseMockProvider, MockError


class GoogleMockProvider(BaseMockProvider):
    """
    Mock provider for Google Generative AI (Gemini) API responses.

    Generates responses matching the Google Generative AI format.
    """

    async def generate_response(self, request_body: dict) -> dict:
        """
        Generate a non-streaming mock response.

        Args:
            request_body: The incoming request body

        Returns:
            dict: Mock response in Google Generative AI format
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            raise error

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        contents = request_body.get("contents", [])

        # Generate response
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)

        # Estimate token usage
        prompt_tokens = self._estimate_input_tokens_google(contents)

        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": content,
                            }
                        ],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                    "index": 0,
                    "safetyRatings": [
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "probability": "NEGLIGIBLE",
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "probability": "NEGLIGIBLE",
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "probability": "NEGLIGIBLE",
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "probability": "NEGLIGIBLE",
                        },
                    ],
                }
            ],
            "usageMetadata": {
                "promptTokenCount": prompt_tokens,
                "candidatesTokenCount": num_tokens,
                "totalTokenCount": prompt_tokens + num_tokens,
            },
        }

    async def generate_stream(self, request_body: dict) -> AsyncGenerator[str, None]:
        """
        Generate a streaming mock response.

        Args:
            request_body: The incoming request body

        Yields:
            str: NDJSON-formatted response chunks in Google format
        """
        # Check for error simulation
        if self._should_error():
            error = self._get_error()
            error_response = {
                "error": {
                    "code": error.status_code,
                    "message": error.message,
                    "status": error.error_type.upper(),
                }
            }
            yield json.dumps(error_response) + "\n"
            return

        # Simulate TTFT delay
        await asyncio.sleep(self._get_ttft_delay())

        # Extract request parameters
        contents = request_body.get("contents", [])

        # Generate content
        num_tokens = self._get_response_tokens()
        content = self._generate_content(num_tokens)
        prompt_tokens = self._estimate_input_tokens_google(contents)

        # Split content into chunks
        words = content.split()
        accumulated_text = ""

        for i, word in enumerate(words):
            accumulated_text += word + (" " if i < len(words) - 1 else "")

            # For Google streaming, each chunk contains the accumulated text
            # Send every few words
            if i % 5 == 0 or i == len(words) - 1:
                is_final = i == len(words) - 1

                chunk = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": accumulated_text,
                                    }
                                ],
                                "role": "model",
                            },
                            "finishReason": "STOP" if is_final else None,
                            "index": 0,
                        }
                    ],
                }

                # Add usage metadata on final chunk
                if is_final:
                    chunk["usageMetadata"] = {
                        "promptTokenCount": prompt_tokens,
                        "candidatesTokenCount": num_tokens,
                        "totalTokenCount": prompt_tokens + num_tokens,
                    }

                yield json.dumps(chunk) + "\n"

            # Inter-token delay
            await asyncio.sleep(self._get_inter_token_delay())

    def _estimate_input_tokens_google(self, contents: list) -> int:
        """Estimate input token count from Google-format contents."""
        total_chars = 0
        for content in contents:
            parts = content.get("parts", [])
            for part in parts:
                if isinstance(part, dict):
                    total_chars += len(part.get("text", ""))
                elif isinstance(part, str):
                    total_chars += len(part)
        # Approximate 4 chars per token
        return total_chars // 4
