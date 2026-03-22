"""
RAG-enabled Agent implementation.

Provides an LLM agent with Retrieval-Augmented Generation capabilities
using connected knowledge bases.
"""

import logging
from typing import Any

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig
from src.services.knowledge_base.rag_service import RAGService

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """
    RAG-enabled LLM agent that retrieves context from knowledge bases.

    This agent automatically retrieves relevant context from connected
    knowledge bases before generating responses, providing more accurate
    and grounded answers.
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_model: Agent,
        db_session: AsyncSession,
        google_client: genai.Client,
    ):
        """
        Initialize RAG agent.

        Args:
            config: Agent configuration
            agent_model: Database agent model
            db_session: Database session
            google_client: Google GenAI client
        """
        super().__init__(config)
        self.agent_model = agent_model
        self.db_session = db_session
        self.rag_service = RAGService(db_session, google_client)
        self._enable_rag = True  # Can be toggled per request

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the RAG agent with context retrieval.

        Args:
            input_data: Dictionary containing:
                - prompt: The user prompt/question
                - context: Optional additional context
                - temperature: Optional temperature override
                - max_tokens: Optional max tokens override
                - enable_rag: Optional flag to enable/disable RAG (default: True)
                - max_context_tokens: Optional max tokens for retrieved context

        Returns:
            Dictionary containing:
                - response: The generated text response
                - model: Model used
                - provider: Provider used
                - sources: List of sources used (if RAG enabled)
                - num_sources: Number of sources retrieved
                - rag_enabled: Whether RAG was used
        """
        if not self.llm_client:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")

        prompt = input_data.get("prompt")
        if not prompt:
            raise ValueError("'prompt' is required in input_data")

        additional_context = input_data.get("context", "")
        temperature = input_data.get("temperature", self.config.llm_config.temperature)
        max_tokens = input_data.get("max_tokens", self.config.llm_config.max_tokens)
        enable_rag = input_data.get("enable_rag", self._enable_rag)
        max_context_tokens = input_data.get("max_context_tokens", 4000)

        try:
            # Check if agent has knowledge bases and RAG is enabled
            has_knowledge_bases = bool(self.agent_model.knowledge_bases)
            use_rag = enable_rag and has_knowledge_bases

            retrieved_context = ""
            sources = []
            num_sources = 0

            if use_rag:
                logger.info(f"Retrieving context for agent {self.agent_model.name}")

                # Retrieve context from knowledge bases
                rag_result = await self.rag_service.augment_prompt_with_context(
                    query=prompt,
                    agent=self.agent_model,
                    system_prompt=self.config.system_prompt,
                    max_context_tokens=max_context_tokens,
                )

                retrieved_context = rag_result["context"]
                sources = rag_result["sources"]
                num_sources = rag_result["num_sources"]

                logger.info(f"Retrieved {num_sources} sources from knowledge bases ({len(retrieved_context)} chars)")

            # Build the full prompt
            full_prompt = ""

            # Add system prompt
            if self.config.system_prompt:
                full_prompt += f"{self.config.system_prompt}\n\n"

            # Add retrieved context if available
            if retrieved_context:
                full_prompt += f"{retrieved_context}\n\n"

            # Add additional context if provided
            if additional_context:
                full_prompt += f"Additional Context: {additional_context}\n\n"

            # Add user prompt
            full_prompt += f"User: {prompt}\n\n"

            # Add instruction to cite sources if RAG is used
            if use_rag and sources:
                full_prompt += (
                    "Please answer the user's query using the retrieved context above. "
                    "When referencing information from the context, cite the source number "
                    "(e.g., [Source 1]). If the context doesn't contain relevant information, "
                    "you may use your general knowledge but clearly indicate that."
                )

            # Generate response using multi-provider client
            response_text = await self.llm_client.generate_content(
                prompt=full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            logger.info(
                f"RAG agent generated response ({len(response_text)} chars) "
                f"using {self.config.llm_config.provider}/{self.config.llm_config.model_name}"
            )

            result = {
                "response": response_text,
                "model": self.config.llm_config.model_name,
                "provider": self.config.llm_config.provider,
                "prompt_length": len(full_prompt),
                "response_length": len(response_text),
                "rag_enabled": use_rag,
                "num_sources": num_sources,
            }

            # Add sources if RAG was used
            if use_rag and sources:
                result["sources"] = sources

            return result

        except Exception as e:
            logger.error(f"RAG agent execution failed: {e}", exc_info=True)
            raise

    def enable_rag(self, enabled: bool = True) -> None:
        """
        Enable or disable RAG for this agent.

        Args:
            enabled: Whether to enable RAG
        """
        self._enable_rag = enabled
        logger.info(f"RAG {'enabled' if enabled else 'disabled'} for agent {self.config.name}")

    def cleanup(self) -> None:
        """Cleanup RAG service resources."""
        if self.rag_service:
            self.rag_service.cleanup()


def create_rag_agent(
    agent_model: Agent,
    db_session: AsyncSession,
    google_client: genai.Client,
    api_key: str | None = None,
) -> RAGAgent:
    """
    Create a RAG-enabled agent from a database model.

    Args:
        agent_model: Database agent model
        db_session: Database session
        google_client: Google GenAI client
        api_key: Optional API key override

    Returns:
        Configured RAG agent
    """
    # Create agent config from model
    config = AgentConfig(
        name=agent_model.name,
        description=agent_model.description or "RAG-enabled agent",
        system_prompt=agent_model.system_prompt
        or "You are a helpful AI assistant with access to a knowledge base. "
        "Provide accurate answers based on the retrieved context.",
    )

    # Create RAG agent
    agent = RAGAgent(
        config=config,
        agent_model=agent_model,
        db_session=db_session,
        google_client=google_client,
    )

    # Initialize client
    if api_key:
        agent.initialize_client(api_key)

    return agent
