"""
Reranking Service for Production-Grade RAG.

Implements cross-encoder reranking to improve retrieval quality.
Supports multiple reranking backends:
- Sentence Transformers Cross-Encoders (local)
- Cohere Rerank API
- LLM-based reranking (fallback)
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class RerankerProvider(StrEnum):
    """Supported reranker providers."""

    CROSS_ENCODER = "cross_encoder"  # Local sentence-transformers
    COHERE = "cohere"  # Cohere Rerank API
    LLM = "llm"  # LLM-based scoring


@dataclass
class RerankResult:
    """Result from reranking."""

    id: str
    original_score: float
    rerank_score: float
    combined_score: float
    payload: dict[str, Any]
    rank: int


class RerankerService:
    """
    Production-grade reranking service for RAG.

    Uses cross-encoders to score query-document pairs directly,
    providing much better relevance ranking than bi-encoder similarity alone.
    """

    # Default cross-encoder model (small and fast, good quality)
    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        provider: RerankerProvider = RerankerProvider.CROSS_ENCODER,
        model_name: str | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the reranker service.

        Args:
            provider: Reranking provider to use
            model_name: Model name (provider-specific)
            config: Provider-specific configuration (API keys, etc.)
        """
        self.provider = provider
        self.model_name = model_name or self.DEFAULT_MODEL
        self.config = config or {}
        self._model = None
        self._client = None
        self._initialized = False

    def _lazy_init(self) -> None:
        """Lazy initialization of the reranker model/client."""
        if self._initialized:
            return

        try:
            if self.provider == RerankerProvider.CROSS_ENCODER:
                self._init_cross_encoder()
            elif self.provider == RerankerProvider.COHERE:
                self._init_cohere()
            # LLM provider doesn't need initialization

            self._initialized = True
            logger.info(f"Initialized reranker: {self.provider.value}/{self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            raise

    def _init_cross_encoder(self) -> None:
        """Initialize sentence-transformers cross-encoder."""
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to LLM reranking")
            self.provider = RerankerProvider.LLM

    def _init_cohere(self) -> None:
        """Initialize Cohere rerank client."""
        try:
            import cohere

            api_key = self.config.get("api_key")
            if not api_key:
                raise ValueError("Cohere API key required for reranking")
            self._client = cohere.Client(api_key)
            self.model_name = self.model_name or "rerank-english-v3.0"
        except ImportError:
            logger.warning("cohere package not installed, falling back to cross-encoder")
            self.provider = RerankerProvider.CROSS_ENCODER
            self._init_cross_encoder()

    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 5,
        score_weight: float = 0.3,
    ) -> list[RerankResult]:
        """
        Rerank search results using cross-encoder scoring.

        Args:
            query: The search query
            results: List of search results with 'payload' containing 'text'
            top_k: Number of top results to return after reranking
            score_weight: Weight for original score in combined score (0-1)
                         combined = (1-weight)*rerank + weight*original

        Returns:
            List of RerankResult objects sorted by combined score
        """
        if not results:
            return []

        self._lazy_init()

        try:
            if self.provider == RerankerProvider.CROSS_ENCODER:
                return self._rerank_cross_encoder(query, results, top_k, score_weight)
            elif self.provider == RerankerProvider.COHERE:
                return self._rerank_cohere(query, results, top_k, score_weight)
            else:
                return self._rerank_llm(query, results, top_k, score_weight)
        except Exception as e:
            logger.error(f"Reranking failed, returning original order: {e}")
            return self._fallback_results(results, top_k)

    def _rerank_cross_encoder(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_weight: float,
    ) -> list[RerankResult]:
        """Rerank using cross-encoder model."""
        # Prepare query-document pairs
        pairs = []
        for result in results:
            text = result.get("payload", {}).get("text", "")
            if not text:
                text = str(result.get("payload", {}))
            pairs.append([query, text])

        # Get cross-encoder scores
        scores = self._model.predict(pairs)

        # Normalize scores to 0-1 range (cross-encoder scores can be any range)
        min_score = min(scores) if len(scores) > 0 else 0
        max_score = max(scores) if len(scores) > 0 else 1
        score_range = max_score - min_score if max_score != min_score else 1
        normalized_scores = [(s - min_score) / score_range for s in scores]

        # Combine with original scores
        rerank_results = []
        for i, (result, rerank_score) in enumerate(zip(results, normalized_scores, strict=False)):
            original_score = result.get("score", 0)
            combined = (1 - score_weight) * rerank_score + score_weight * original_score

            rerank_results.append(
                RerankResult(
                    id=result.get("id", f"result_{i}"),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    combined_score=combined,
                    payload=result.get("payload", {}),
                    rank=0,  # Will be set after sorting
                )
            )

        # Sort by combined score and assign ranks
        rerank_results.sort(key=lambda x: x.combined_score, reverse=True)
        for i, result in enumerate(rerank_results[:top_k]):
            result.rank = i + 1

        logger.info(f"Reranked {len(results)} results with cross-encoder, returning top {top_k}")
        return rerank_results[:top_k]

    def _rerank_cohere(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_weight: float,
    ) -> list[RerankResult]:
        """Rerank using Cohere Rerank API."""
        # Extract documents
        documents = []
        for result in results:
            text = result.get("payload", {}).get("text", "")
            if not text:
                text = str(result.get("payload", {}))
            documents.append(text)

        # Call Cohere rerank
        response = self._client.rerank(
            model=self.model_name,
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
        )

        # Build results
        rerank_results = []
        for i, rerank_item in enumerate(response.results):
            idx = rerank_item.index
            original_result = results[idx]
            original_score = original_result.get("score", 0)
            rerank_score = rerank_item.relevance_score
            combined = (1 - score_weight) * rerank_score + score_weight * original_score

            rerank_results.append(
                RerankResult(
                    id=original_result.get("id", f"result_{idx}"),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    combined_score=combined,
                    payload=original_result.get("payload", {}),
                    rank=i + 1,
                )
            )

        logger.info(f"Reranked {len(results)} results with Cohere, returning top {top_k}")
        return rerank_results

    def _rerank_llm(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_weight: float,
    ) -> list[RerankResult]:
        """
        Fallback LLM-based reranking using simple heuristics.

        Uses keyword matching and text overlap as a lightweight reranking method
        when cross-encoder or API-based reranking is not available.
        """
        import re

        # Extract query keywords (simple tokenization)
        query_keywords = set(re.findall(r"\b\w{3,}\b", query.lower()))

        rerank_results = []
        for i, result in enumerate(results):
            text = result.get("payload", {}).get("text", "").lower()
            original_score = result.get("score", 0)

            # Calculate keyword overlap score
            text_words = set(re.findall(r"\b\w{3,}\b", text))
            overlap = len(query_keywords & text_words)
            keyword_score = overlap / max(len(query_keywords), 1)

            # Calculate exact phrase match bonus
            phrase_bonus = 0.2 if query.lower() in text else 0

            # Combine scores
            rerank_score = min(keyword_score + phrase_bonus, 1.0)
            combined = (1 - score_weight) * rerank_score + score_weight * original_score

            rerank_results.append(
                RerankResult(
                    id=result.get("id", f"result_{i}"),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    combined_score=combined,
                    payload=result.get("payload", {}),
                    rank=0,
                )
            )

        # Sort and assign ranks
        rerank_results.sort(key=lambda x: x.combined_score, reverse=True)
        for i, result in enumerate(rerank_results[:top_k]):
            result.rank = i + 1

        logger.info(f"Reranked {len(results)} results with keyword heuristics, returning top {top_k}")
        return rerank_results[:top_k]

    def _fallback_results(
        self,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> list[RerankResult]:
        """Convert results to RerankResult without actual reranking."""
        rerank_results = []
        for i, result in enumerate(results[:top_k]):
            score = result.get("score", 0)
            rerank_results.append(
                RerankResult(
                    id=result.get("id", f"result_{i}"),
                    original_score=score,
                    rerank_score=score,
                    combined_score=score,
                    payload=result.get("payload", {}),
                    rank=i + 1,
                )
            )
        return rerank_results


# Singleton instance for reuse
_reranker_instance: RerankerService | None = None


def get_reranker(
    provider: RerankerProvider = RerankerProvider.CROSS_ENCODER,
    model_name: str | None = None,
    config: dict[str, Any] | None = None,
) -> RerankerService:
    """Get or create a reranker service instance."""
    global _reranker_instance

    if _reranker_instance is None:
        _reranker_instance = RerankerService(
            provider=provider,
            model_name=model_name,
            config=config,
        )

    return _reranker_instance
