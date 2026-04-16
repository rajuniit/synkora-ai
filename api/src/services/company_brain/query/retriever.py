"""
Multi-source parallel retriever for Company Brain.

Runs searches against the configured backend for each relevant source type
in parallel, then returns all results for the assembler to merge and rank.

The retriever also handles:
  - Metadata pre-filtering (cuts search space 10-100x before scoring)
  - Per-source result limits
  - PageIndex routing for long-form documents (optional)
"""

import asyncio
import logging
from typing import Any

from src.services.company_brain.search.base import SearchFilter, SearchResult
from src.services.company_brain.search.factory import get_search_backend

from .router import QueryIntent

logger = logging.getLogger(__name__)

# How many results to pull per source before merging
_DEFAULT_PER_SOURCE_LIMIT = 10


async def retrieve(
    tenant_id: str,
    query: str,
    intent: QueryIntent,
    limit: int = 20,
) -> list[SearchResult]:
    """
    Run parallel searches for each source type implied by the intent.

    Args:
        tenant_id: Scopes all searches to this tenant.
        query:     User's natural language query.
        intent:    Routing intent from the query router.
        limit:     Total results to return after merging.

    Returns:
        List of SearchResult sorted by score (descending), capped at `limit`.
    """
    backend = get_search_backend()
    source_types = intent.source_types or _all_source_types()

    filters = SearchFilter(
        source_types=source_types,
        time_from=intent.time_from,
        time_to=intent.time_to,
        storage_tiers=intent.tiers,
    )

    per_source_limit = max(_DEFAULT_PER_SOURCE_LIMIT, limit)

    if len(source_types) <= 1:
        # Single source — one direct search
        try:
            response = await backend.search(
                tenant_id=tenant_id,
                query=query,
                filters=filters,
                limit=limit,
            )
            return response.results
        except Exception as exc:
            logger.error("Retriever search failed: %s", exc)
            return []

    # Multiple sources — search each in parallel with per-source limit
    tasks = []
    for source_type in source_types:
        source_filter = SearchFilter(
            source_types=[source_type],
            time_from=intent.time_from,
            time_to=intent.time_to,
            storage_tiers=intent.tiers,
        )
        tasks.append(_search_source(backend, tenant_id, query, source_filter, per_source_limit))

    results_per_source = await asyncio.gather(*tasks, return_exceptions=True)
    all_results: list[SearchResult] = []

    for source_type, result in zip(source_types, results_per_source, strict=False):
        if isinstance(result, Exception):
            logger.warning("Search failed for source %s: %s", source_type, result)
        else:
            all_results.extend(result)

    # If PageIndex is enabled for long-form doc sources, fetch and merge those too
    if intent.use_pageindex:
        pageindex_results = await _fetch_pageindex(tenant_id, query, intent)
        all_results.extend(pageindex_results)

    # Sort by score (RRF or plain score) — assembler will re-rank with dedup
    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results[:limit]


async def _search_source(
    backend: Any,
    tenant_id: str,
    query: str,
    filters: SearchFilter,
    limit: int,
) -> list[SearchResult]:
    try:
        resp = await backend.search(tenant_id=tenant_id, query=query, filters=filters, limit=limit)
        return resp.results
    except Exception as exc:
        logger.warning("Source search failed (%s): %s", filters.source_types, exc)
        return []


async def _fetch_pageindex(
    tenant_id: str,
    query: str,
    intent: QueryIntent,
) -> list[SearchResult]:
    """
    Placeholder for PageIndex integration.

    When COMPANY_BRAIN_ENABLE_PAGEINDEX=true and the intent is deep_doc,
    route the query through the PageIndex tree search for Confluence / Notion docs.
    Returns an empty list until the PageIndex client is wired up.
    """
    logger.debug("PageIndex routing requested but not yet implemented — skipping")
    return []


def _all_source_types() -> list[str]:
    """Return all known source types (used when intent has no specific source)."""
    return [
        "slack",
        "github",
        "gitlab",
        "jira",
        "clickup",
        "notion",
        "confluence",
        "gmail",
        "google_drive",
        "linear",
    ]
