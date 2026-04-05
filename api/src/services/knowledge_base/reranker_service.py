"""
Reranking Service for Production-Grade RAG.

The ``cross_encoder`` provider is delegated to the ML microservice so that
``sentence-transformers`` is not required in the API image.
"""

import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


def _run_async(coro) -> object:
    """Run an async coroutine safely from synchronous code.

    Uses a dedicated thread so this works whether or not there is already a
    running event loop in the calling context (FastAPI, Celery, tests, etc.).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()

logger = logging.getLogger(__name__)


class RerankerProvider(StrEnum):
    """Supported reranker providers."""

    CROSS_ENCODER = "cross_encoder"  # ML microservice
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
    """Production-grade reranking service for RAG."""

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        provider: RerankerProvider = RerankerProvider.CROSS_ENCODER,
        model_name: str | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.provider = provider
        self.model_name = model_name or self.DEFAULT_MODEL
        self.config = config or {}
        self._client = None
        self._initialized = False

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        try:
            if self.provider == RerankerProvider.COHERE:
                self._init_cohere()
            # CROSS_ENCODER and LLM don't need initialization here
            self._initialized = True
            logger.info(f"Initialized reranker: {self.provider.value}/{self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            raise

    def _init_cohere(self) -> None:
        try:
            import cohere

            api_key = self.config.get("api_key")
            if not api_key:
                raise ValueError("Cohere API key required for reranking")
            self._client = cohere.Client(api_key)
            self.model_name = self.model_name or "rerank-english-v3.0"
        except ImportError:
            logger.warning("cohere package not installed, falling back to cross-encoder via ML service")
            self.provider = RerankerProvider.CROSS_ENCODER

    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 5,
        score_weight: float = 0.3,
    ) -> list[RerankResult]:
        """Rerank search results using cross-encoder scoring."""
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
        """Rerank via ML microservice cross-encoder."""
        from src.core.ml_client import get_ml_client

        client = get_ml_client()
        raw = _run_async(
            client.rerank(
                query=query,
                results=results,
                top_k=top_k,
                score_weight=score_weight,
                model=self.model_name,
            )
        )
        rerank_results = []
        for item in raw:
            rerank_results.append(
                RerankResult(
                    id=item["id"],
                    original_score=item["original_score"],
                    rerank_score=item["rerank_score"],
                    combined_score=item["combined_score"],
                    payload=item["payload"],
                    rank=item["rank"],
                )
            )
        logger.info(f"Reranked {len(results)} results with ML cross-encoder, returning top {top_k}")
        return rerank_results

    def _rerank_cohere(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
        score_weight: float,
    ) -> list[RerankResult]:
        """Rerank using Cohere Rerank API."""
        documents = []
        for result in results:
            text = result.get("payload", {}).get("text", "")
            if not text:
                text = str(result.get("payload", {}))
            documents.append(text)

        response = self._client.rerank(
            model=self.model_name,
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
        )

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
        """Fallback LLM-based reranking using keyword heuristics."""
        import re

        query_keywords = set(re.findall(r"\b\w{3,}\b", query.lower()))
        rerank_results = []
        for i, result in enumerate(results):
            text = result.get("payload", {}).get("text", "").lower()
            original_score = result.get("score", 0)
            text_words = set(re.findall(r"\b\w{3,}\b", text))
            overlap = len(query_keywords & text_words)
            keyword_score = overlap / max(len(query_keywords), 1)
            phrase_bonus = 0.2 if query.lower() in text else 0
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

        rerank_results.sort(key=lambda x: x.combined_score, reverse=True)
        for i, result in enumerate(rerank_results[:top_k]):
            result.rank = i + 1
        logger.info(f"Reranked {len(results)} results with keyword heuristics, returning top {top_k}")
        return rerank_results[:top_k]

    def _fallback_results(self, results: list[dict[str, Any]], top_k: int) -> list[RerankResult]:
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


_reranker_instance: RerankerService | None = None


def get_reranker(
    provider: RerankerProvider = RerankerProvider.CROSS_ENCODER,
    model_name: str | None = None,
    config: dict[str, Any] | None = None,
) -> RerankerService:
    """Get or create a reranker service instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = RerankerService(provider=provider, model_name=model_name, config=config)
    return _reranker_instance
