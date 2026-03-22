"""
LLM Agent implementation using Google Agent SDK.

Provides a general-purpose LLM agent for text generation and conversation.
"""

import logging
from typing import Any

from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """
    General-purpose LLM agent using Google's Gemini models.

    This agent can handle various text-based tasks including:
    - Question answering
    - Text generation
    - Summarization
    - Translation
    - And more
    """

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the LLM agent.

        Args:
            input_data: Dictionary containing:
                - prompt: The user prompt/question
                - context: Optional context for the conversation
                - temperature: Optional temperature override
                - max_tokens: Optional max tokens override

        Returns:
            Dictionary containing:
                - response: The generated text response
                - model: Model used
                - provider: Provider used
        """
        if not self.llm_client:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")

        prompt = input_data.get("prompt")
        if not prompt:
            raise ValueError("'prompt' is required in input_data")

        context = input_data.get("context", "")
        temperature = input_data.get("temperature", self.config.llm_config.temperature)
        max_tokens = input_data.get("max_tokens", self.config.llm_config.max_tokens)
        system_prompt = input_data.get("system_prompt", self.config.system_prompt)

        try:
            # Build the full prompt
            full_prompt = ""
            if system_prompt:
                full_prompt += f"{system_prompt}\n\n"
            if context:
                full_prompt += f"Context: {context}\n\n"
            full_prompt += f"User: {prompt}"

            # Generate response using multi-provider client
            response_text = await self.llm_client.generate_content(
                prompt=full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            logger.info(
                f"LLM agent generated response ({len(response_text)} chars) "
                f"using {self.config.llm_config.provider}/{self.config.llm_config.model_name}"
            )

            return {
                "response": response_text,
                "model": self.config.llm_config.model_name,
                "provider": self.config.llm_config.provider,
                "prompt_length": len(full_prompt),
                "response_length": len(response_text),
            }

        except Exception as e:
            logger.error(f"LLM agent execution failed: {e}", exc_info=True)
            raise


# Example usage function
def create_llm_agent(api_key: str, system_prompt: str = None) -> LLMAgent:
    """
    Create a pre-configured LLM agent.

    Args:
        api_key: Google API key
        system_prompt: Optional system prompt

    Returns:
        Configured LLM agent
    """
    config = AgentConfig(
        name="llm_agent",
        description="General-purpose LLM agent for text generation",
        system_prompt=system_prompt
        or "You are a helpful AI assistant. Provide clear, accurate, and concise responses.",
    )

    agent = LLMAgent(config)
    agent.initialize_client(api_key)

    return agent
