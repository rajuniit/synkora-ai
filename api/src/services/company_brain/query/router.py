"""
Query router for Company Brain.

Uses a cheap LLM (claude-haiku by default) to classify the incoming query
into an intent that determines how the retriever routes it.

Intent schema:
  {
    "intent":        "recent" | "historical" | "deep_doc" | "code" | "entity" | "cross_source",
    "source_types":  ["slack", "github", ...],   // empty = all sources
    "time_range":    {"from": "ISO", "to": "ISO"} | null,
    "entities":      ["alice", "payments-api"],   // named entities in query
    "use_pageindex": bool,                        // only true for deep_doc + long sources
    "tiers":         ["hot"] | ["hot", "warm"]   // which storage tiers to search
  }

Cost: ~$0.0001 per query with claude-haiku.
Fallback: if classification fails, returns a safe default intent (all sources, hot tier).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryIntent:
    intent: str = "cross_source"                    # routing intent
    source_types: list[str] = field(default_factory=list)   # empty = all
    time_from: str | None = None
    time_to: str | None = None
    entities: list[str] = field(default_factory=list)
    use_pageindex: bool = False
    tiers: list[str] = field(default_factory=lambda: ["hot"])


_SYSTEM_PROMPT = """You are a query classifier for a Company Brain (enterprise data hub).
Classify the user query and return a JSON object with these fields:

intent: one of
  "recent"       — asking about something that happened recently (last 7 days)
  "historical"   — asking about something from the distant past
  "deep_doc"     — asking for detailed information from long documents (design docs, specs, runbooks)
  "code"         — asking about code, PRs, commits, or technical implementation
  "entity"       — asking about a specific person, team, or project
  "cross_source" — general question spanning multiple sources (default)

source_types: array of relevant sources from: slack, github, gitlab, jira, clickup, notion, confluence, gmail, google_drive.
  Empty array = search all sources.

time_from: ISO-8601 date string if query implies a time window start, else null.
time_to:   ISO-8601 date string if query implies a time window end, else null.

entities: array of named entities (people, projects, repos, teams) mentioned in the query.

use_pageindex: true only if intent=deep_doc AND source_types contains notion or confluence.

tiers: array of storage tiers to search. Use ["hot"] for recent queries, ["hot","warm"] for historical.

Respond with ONLY valid JSON, no markdown, no explanation."""


async def classify_query(query: str) -> QueryIntent:
    """
    Classify the user query into a routing intent.

    Falls back to a safe default intent if the LLM call fails.
    """
    from src.config.settings import get_settings
    settings = get_settings()
    model = getattr(settings, "company_brain_query_router_model", "claude-haiku-4-5-20251001")
    enable_pageindex = getattr(settings, "company_brain_enable_pageindex", False)

    try:
        import litellm
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=300,
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        data: dict[str, Any] = json.loads(raw)

        use_pi = bool(data.get("use_pageindex")) and enable_pageindex
        tiers = data.get("tiers") or ["hot"]
        if not isinstance(tiers, list):
            tiers = ["hot"]

        return QueryIntent(
            intent=data.get("intent", "cross_source"),
            source_types=data.get("source_types") or [],
            time_from=data.get("time_from"),
            time_to=data.get("time_to"),
            entities=data.get("entities") or [],
            use_pageindex=use_pi,
            tiers=tiers,
        )

    except Exception as exc:
        logger.warning("Query classification failed (%s): returning default intent", exc)
        return _default_intent(query)


def _default_intent(query: str) -> QueryIntent:
    """Safe default when classification fails: search everything, hot tier only."""
    query_lower = query.lower()

    # Simple heuristics as fallback
    recent_signals = ["today", "this week", "recently", "just now", "latest", "yesterday"]
    historical_signals = ["last year", "months ago", "when did", "history of", "originally"]
    code_signals = ["pr ", "pull request", "commit", "branch", "merge", "code", "function", "bug"]

    tiers = ["hot"]
    if any(s in query_lower for s in historical_signals):
        tiers = ["hot", "warm"]

    return QueryIntent(
        intent="recent" if any(s in query_lower for s in recent_signals) else
               "code" if any(s in query_lower for s in code_signals) else
               "cross_source",
        tiers=tiers,
    )
