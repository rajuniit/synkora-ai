"""
Context assembler for Company Brain.

Takes the raw retrieval results from multiple sources, deduplicates by content
hash, re-ranks with Reciprocal Rank Fusion (RRF), trims to the token budget,
and formats a context string with citations for the answer LLM.

Output:
  {
    "context":   str,          # formatted context block for the LLM prompt
    "citations": list[dict],   # structured citation list for the frontend
    "token_count": int,
    "result_count": int,
  }
"""

import hashlib
import logging
from typing import Any

from src.services.company_brain.search.base import SearchResult

logger = logging.getLogger(__name__)


def assemble(
    results: list[SearchResult],
    query: str,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """
    Assemble retrieval results into a context block for the answer LLM.

    Args:
        results:    Raw SearchResults from the retriever (may contain duplicates).
        query:      Original user query (unused here, available for future re-ranking).
        max_tokens: Token budget for the context block.  Reads from settings if None.

    Returns:
        Dict with "context", "citations", "token_count", "result_count".
    """
    if max_tokens is None:
        from src.config.settings import get_settings
        max_tokens = getattr(get_settings(), "company_brain_context_tokens", 32_000)

    # 1. Deduplicate by content hash (different sources may index the same text)
    deduped = _deduplicate(results)

    # 2. Re-rank with RRF (combine scores from different sources/queries)
    ranked = _rrf_rank(deduped)

    # 3. Trim to token budget
    trimmed, token_count = _trim_to_budget(ranked, max_tokens)

    # 4. Format context + citations
    context_parts = []
    citations = []

    for i, result in enumerate(trimmed, 1):
        source_label = _source_label(result)
        context_parts.append(f"[{i}] {source_label}\n{result.content}\n")
        citations.append({
            "index": i,
            "source": result.source_type,
            "title": result.title,
            "url": result.source_url,
            "occurred_at": result.occurred_at,
            "score": round(result.score, 4),
            "metadata": {
                k: v for k, v in (result.metadata or {}).items()
                if k not in ("tenant_id",)  # never expose tenant_id
            },
        })

    context = "\n".join(context_parts)

    return {
        "context": context,
        "citations": citations,
        "token_count": token_count,
        "result_count": len(trimmed),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _deduplicate(results: list[SearchResult]) -> list[SearchResult]:
    """Remove results with near-identical content (same hash)."""
    seen: set[str] = set()
    out: list[SearchResult] = []
    for r in results:
        h = _content_hash(r.content[:500])  # hash first 500 chars
        if h not in seen:
            seen.add(h)
            out.append(r)
    return out


def _rrf_rank(results: list[SearchResult], k: int = 60) -> list[SearchResult]:
    """
    Reciprocal Rank Fusion across a mixed list of results from different sources.

    Each result already has a backend score.  RRF re-ranks by combining the
    position-based score (1/(k+rank)) with the original normalised score.
    """
    # Give each result its position-based RRF component
    scored = []
    for rank, result in enumerate(results):
        rrf_score = 1.0 / (k + rank + 1)
        # Blend RRF (60%) + original score (40%)
        combined = 0.6 * rrf_score * 60 + 0.4 * result.score
        scored.append((combined, result))

    scored.sort(key=lambda x: x[0], reverse=True)
    for i, (score, result) in enumerate(scored):
        result.score = score
    return [r for _, r in scored]


def _approx_tokens(text: str) -> int:
    """Approximate token count without a hard tiktoken dependency."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def _trim_to_budget(
    results: list[SearchResult],
    max_tokens: int,
) -> tuple[list[SearchResult], int]:
    """Keep as many results as fit within the token budget."""
    total = 0
    kept: list[SearchResult] = []
    for result in results:
        chunk_tokens = _approx_tokens(result.content)
        if total + chunk_tokens > max_tokens:
            break
        kept.append(result)
        total += chunk_tokens
    return kept, total


def _source_label(result: SearchResult) -> str:
    """Human-readable label for the source block header."""
    meta = result.metadata or {}
    parts = [result.source_type.upper()]

    if result.title:
        parts.append(result.title)
    elif meta.get("channel"):
        parts.append(f"#{meta['channel']}")
    elif meta.get("repo"):
        parts.append(meta["repo"])

    if result.occurred_at:
        parts.append(f"({result.occurred_at[:10]})")

    return " | ".join(parts)
