"""GitHub daily digest extractor."""

import logging
from datetime import date as DateType
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base import DIGEST_JSON_SCHEMA, BaseDigestExtractor, RawItem

logger = logging.getLogger(__name__)


class GithubDigestExtractor(BaseDigestExtractor):
    """Extracts daily digest from a GitHub data source."""

    @property
    def source_type(self) -> str:
        return "GITHUB"

    async def fetch_items(
        self,
        data_source: DataSource,
        start: datetime,
        end: datetime,
        db: AsyncSession,
    ) -> list[RawItem]:
        from src.services.data_sources.github_connector import GitHubConnector

        connector = GitHubConnector(data_source, db)
        connected = await connector.connect()
        if not connected:
            logger.warning(f"Could not connect to GitHub data source {data_source.id}")
            return []

        try:
            documents = await connector.fetch_documents(since=start)
        finally:
            await connector.disconnect()

        items = []
        for doc in documents:
            meta = doc.get("metadata", {})
            item_type = meta.get("type", "item")
            repo = meta.get("repository", "unknown")
            title = meta.get("title", doc.get("text", "")[:100])
            author = meta.get("author", meta.get("user", "unknown"))
            text = f"[{repo}] [{item_type}] {title} — by {author}"
            items.append(RawItem(text=text, metadata=meta))

        return items

    def build_prompt(self, items: list[RawItem], target_date: DateType) -> str:
        content = "\n".join(f"- {item.text}" for item in items)
        if not content:
            content = "(no activity)"

        # Aggregate counts by type for context
        type_counts: dict[str, int] = {}
        for item in items:
            t = item.metadata.get("type", "other")
            type_counts[t] = type_counts.get(t, 0) + 1
        counts_summary = ", ".join(f"{v} {k}(s)" for k, v in type_counts.items())

        return f"""You are analyzing GitHub repository activity for {target_date.isoformat()}.

Activity ({len(items)} total: {counts_summary}):
{content}

Extract a structured summary. Return ONLY valid JSON matching this schema:
{DIGEST_JSON_SCHEMA}

For source_specific include:
  "repository_breakdown": [{{"repo": "name", "prs_merged": N, "issues_closed": N, "commits": N}}],
  "top_contributors": ["username", ...]

Rules:
- highlights: significant merges, releases, major issues
- key_decisions: architectural decisions, deprecation notices
- action_items: open PRs needing review, blocking issues
- activity_level: low (<10 items), medium (10-50), high (>50)
"""
