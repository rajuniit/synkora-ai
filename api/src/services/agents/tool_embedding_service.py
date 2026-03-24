"""
Tool Embedding Service

Provides semantic tool retrieval by delegating embedding and FAISS operations
to the ML microservice (synkora-ml).  No local sentence-transformers or faiss
required in the API image.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ToolEmbeddingConfig:
    """Configuration for tool embeddings."""

    provider: str = "sentence_transformers"
    model_name: str = "all-MiniLM-L6-v2"
    config: dict | None = None


class ToolEmbeddingService:
    """
    In-memory tool embedding service backed by the ML microservice.

    The ML service builds and caches the FAISS index per agent_id
    (1 hour TTL).  This class is a thin coordinator.
    """

    _instance: ToolEmbeddingService | None = None
    _initialized: bool = False

    def __new__(cls) -> ToolEmbeddingService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if ToolEmbeddingService._initialized:
            return
        self._ready: bool = False
        self._agent_id: str | None = None
        ToolEmbeddingService._initialized = True

    def initialize(
        self,
        tools: list[dict[str, Any]],
        embedding_config: ToolEmbeddingConfig | None = None,
        agent_id: str = "default",
    ) -> None:
        """Send tool definitions to the ML microservice to build a FAISS index."""
        if not tools:
            logger.warning("No tools provided for embedding initialization")
            return

        from src.core.ml_client import get_ml_client

        client = get_ml_client()
        try:
            asyncio.run(client.initialize_tools(agent_id=agent_id, tools=tools))
            self._agent_id = agent_id
            self._ready = True
            logger.info(f"Tool embeddings initialized via ML service for agent={agent_id}, count={len(tools)}")
        except Exception as e:
            logger.error(f"Failed to initialize tool embeddings via ML service: {e}")
            self._ready = False

    def is_initialized(self) -> bool:
        return self._ready and self._agent_id is not None

    def find_similar_tools(
        self,
        query: str,
        limit: int = 15,
        score_threshold: float = 0.3,
        agent_id: str | None = None,
    ) -> list[tuple[str, float]]:
        """Find tools semantically similar to the query via ML microservice."""
        target_agent_id = agent_id or self._agent_id
        if not target_agent_id:
            logger.debug("Tool embeddings not initialized (no agent_id)")
            return []

        from src.core.ml_client import get_ml_client

        client = get_ml_client()
        try:
            return asyncio.run(
                client.search_tools(
                    agent_id=target_agent_id,
                    query=query,
                    limit=limit,
                    threshold=score_threshold,
                )
            )
        except Exception as e:
            logger.error(f"Error in ML service tool search: {e}")
            return []

    def find_similar_tool_names(
        self,
        query: str,
        limit: int = 15,
        score_threshold: float = 0.3,
        agent_id: str | None = None,
    ) -> list[str]:
        results = self.find_similar_tools(query, limit, score_threshold, agent_id)
        return [tool_name for tool_name, _ in results]

    def reset(self) -> None:
        self._ready = False
        self._agent_id = None


_tool_embedding_service: ToolEmbeddingService | None = None


def get_tool_embedding_service() -> ToolEmbeddingService:
    global _tool_embedding_service
    if _tool_embedding_service is None:
        _tool_embedding_service = ToolEmbeddingService()
    return _tool_embedding_service


def initialize_tool_embeddings(
    tools: list[dict[str, Any]],
    provider: str = "sentence_transformers",
    model_name: str = "all-MiniLM-L6-v2",
    config: dict | None = None,
    agent_id: str = "default",
) -> ToolEmbeddingService:
    """Convenience function to initialize tool embeddings."""
    service = get_tool_embedding_service()
    embedding_config = ToolEmbeddingConfig(provider=provider, model_name=model_name, config=config)
    service.initialize(tools, embedding_config, agent_id=agent_id)
    return service
