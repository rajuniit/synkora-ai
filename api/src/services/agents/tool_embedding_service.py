"""
Tool Embedding Service

Provides semantic tool retrieval using in-memory FAISS vector store.
Tools are embedded once on initialization and can be queried by semantic similarity.

This enables finding tools even when user queries use different terminology
than the tool names/descriptions (e.g., "notify team" → slack tools).

Uses the existing EmbeddingService which supports multiple providers:
- sentence_transformers (default, no API key needed)
- OPENAI
- cohere
- huggingface
- LITELLM
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from src.services.knowledge_base.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ToolEmbeddingConfig:
    """Configuration for tool embeddings."""

    provider: str = "sentence_transformers"  # Default: local, no API key needed
    model_name: str = "all-MiniLM-L6-v2"  # Fast and good quality
    config: dict | None = None  # Provider-specific config (api_key, etc.)


class ToolEmbeddingService:
    """
    In-memory tool embedding service using FAISS.

    Embeds tool descriptions and example queries, then retrieves
    semantically similar tools for a given user query.

    Uses the existing EmbeddingService infrastructure which supports
    multiple providers (sentence_transformers, OPENAI, cohere, LITELLM, etc.)
    """

    _instance: ToolEmbeddingService | None = None
    _initialized: bool = False

    def __new__(cls) -> ToolEmbeddingService:
        """Singleton pattern - only one instance needed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the service (only runs once due to singleton)."""
        if ToolEmbeddingService._initialized:
            return

        self._faiss_index: Any | None = None
        self._tool_names: list[str] = []
        self._embedding_service: EmbeddingService | None = None
        self._embedding_dim: int = 0

        ToolEmbeddingService._initialized = True

    def initialize(
        self,
        tools: list[dict[str, Any]],
        embedding_config: ToolEmbeddingConfig | None = None,
    ) -> None:
        """
        Initialize the vector store with tool embeddings.

        Args:
            tools: List of tool definitions with 'name' and 'description' keys.
                   Optionally include 'example_queries' for better matching.
            embedding_config: Embedding configuration. If None, uses default
                             sentence_transformers (local, no API key needed).
        """
        if not tools:
            logger.warning("No tools provided for embedding initialization")
            return

        if embedding_config is None:
            embedding_config = ToolEmbeddingConfig()

        try:
            # Import FAISS
            try:
                import faiss
            except ImportError:
                logger.warning("faiss-cpu not installed, tool embeddings disabled")
                return

            # Initialize embedding service
            from src.services.knowledge_base.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService(
                provider=embedding_config.provider,
                model_name=embedding_config.model_name,
                config=embedding_config.config or {},
            )

            # Prepare texts to embed
            texts: list[str] = []
            self._tool_names = []

            for tool in tools:
                tool_name = tool.get("name", "")
                description = tool.get("description", "")
                example_queries = tool.get("example_queries", [])

                if not tool_name:
                    continue

                # Create searchable text combining name, description, and examples
                name_words = tool_name.replace("internal_", "").replace("_", " ")
                text_parts = [name_words, description]

                if example_queries:
                    text_parts.extend(example_queries)

                searchable_text = " ".join(text_parts)
                texts.append(searchable_text)
                self._tool_names.append(tool_name)

            if not texts:
                logger.warning("No valid tools to embed")
                return

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} tools...")
            embeddings = self._embedding_service.embed_texts(texts)

            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            self._embedding_dim = embeddings_array.shape[1]

            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings_array)

            # Create FAISS index (Inner Product after normalization = Cosine Similarity)
            self._faiss_index = faiss.IndexFlatIP(self._embedding_dim)
            self._faiss_index.add(embeddings_array)

            logger.info(
                f"Tool embedding service initialized with {len(texts)} tools "
                f"(provider={embedding_config.provider}, model={embedding_config.model_name}, "
                f"dim={self._embedding_dim})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize tool embeddings: {e}")
            self._faiss_index = None
            self._embedding_service = None

    def is_initialized(self) -> bool:
        """Check if the vector store is initialized and ready."""
        return self._faiss_index is not None and self._embedding_service is not None

    def find_similar_tools(
        self,
        query: str,
        limit: int = 15,
        score_threshold: float = 0.3,
    ) -> list[tuple[str, float]]:
        """
        Find tools semantically similar to the query.

        Args:
            query: User's message/query
            limit: Maximum number of tools to return
            score_threshold: Minimum similarity score (0-1, higher = more similar)

        Returns:
            List of (tool_name, similarity_score) tuples, sorted by score descending
        """
        if not self.is_initialized():
            logger.debug("Tool embeddings not initialized, returning empty results")
            return []

        try:
            import faiss

            # Embed the query
            query_embedding = self._embedding_service.embed_text(query)
            query_array = np.array([query_embedding], dtype=np.float32)

            # Normalize for cosine similarity
            faiss.normalize_L2(query_array)

            # Search
            scores, indices = self._faiss_index.search(query_array, min(limit, len(self._tool_names)))

            # Filter by threshold and build results
            similar_tools: list[tuple[str, float]] = []
            for score, idx in zip(scores[0], indices[0], strict=True):
                if idx >= 0 and score >= score_threshold:
                    tool_name = self._tool_names[idx]
                    similar_tools.append((tool_name, float(score)))

            logger.debug(f"Embedding search for '{query[:50]}...' found {len(similar_tools)} tools")
            return similar_tools

        except Exception as e:
            logger.error(f"Error in embedding search: {e}")
            return []

    def find_similar_tool_names(
        self,
        query: str,
        limit: int = 15,
        score_threshold: float = 0.3,
    ) -> list[str]:
        """
        Find tool names semantically similar to the query.

        Convenience method that returns just the tool names without scores.
        """
        results = self.find_similar_tools(query, limit, score_threshold)
        return [tool_name for tool_name, _ in results]

    def reset(self) -> None:
        """Reset the service (useful for testing or reinitialization)."""
        self._faiss_index = None
        self._tool_names = []
        self._embedding_service = None
        self._embedding_dim = 0


# Global singleton instance
_tool_embedding_service: ToolEmbeddingService | None = None


def get_tool_embedding_service() -> ToolEmbeddingService:
    """Get the global tool embedding service instance."""
    global _tool_embedding_service
    if _tool_embedding_service is None:
        _tool_embedding_service = ToolEmbeddingService()
    return _tool_embedding_service


def initialize_tool_embeddings(
    tools: list[dict[str, Any]],
    provider: str = "sentence_transformers",
    model_name: str = "all-MiniLM-L6-v2",
    config: dict | None = None,
) -> ToolEmbeddingService:
    """
    Convenience function to initialize tool embeddings with custom config.

    Args:
        tools: List of tool definitions
        provider: Embedding provider ('sentence_transformers', 'OPENAI', 'LITELLM', etc.)
        model_name: Model name for the provider
        config: Provider-specific config (api_key, api_base, etc.)

    Returns:
        Initialized ToolEmbeddingService instance
    """
    service = get_tool_embedding_service()
    embedding_config = ToolEmbeddingConfig(
        provider=provider,
        model_name=model_name,
        config=config,
    )
    service.initialize(tools, embedding_config)
    return service
