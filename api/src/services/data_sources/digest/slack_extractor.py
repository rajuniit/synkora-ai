"""Slack daily digest extractor."""

import logging
from datetime import date as DateType
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base import DIGEST_JSON_SCHEMA, BaseDigestExtractor, RawItem

logger = logging.getLogger(__name__)


class SlackDigestExtractor(BaseDigestExtractor):
    """Extracts daily digest from a Slack data source."""

    @property
    def source_type(self) -> str:
        return "SLACK"

    async def fetch_items(
        self,
        data_source: DataSource,
        start: datetime,
        end: datetime,
        db: AsyncSession,
    ) -> list[RawItem]:
        from src.services.data_sources.slack_connector import SlackConnector

        connector = SlackConnector(data_source, db)
        connected = await connector.connect()
        if not connected:
            logger.warning(f"Could not connect to Slack data source {data_source.id}")
            return []

        try:
            documents = await connector.fetch_documents(since=start)
        finally:
            await connector.disconnect()

        items = []
        for doc in documents:
            ts_str = doc.get("metadata", {}).get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str) if ts_str else None
            except ValueError:
                ts = None

            # Filter to target day
            if ts and not (start <= ts < end):
                continue

            meta = doc.get("metadata", {})
            channel = meta.get("channel", "unknown")
            user = meta.get("user", "unknown")
            label = f"[#{channel}] {user}: " if channel != "unknown" else ""
            items.append(RawItem(text=f"{label}{doc.get('text', '')}", metadata=meta))

        return items

    def build_prompt(self, items: list[RawItem], target_date: DateType) -> str:
        if not items:
            return f"""You are analyzing Slack workspace activity for {target_date.isoformat()}.
No messages found.
Return ONLY valid JSON: {DIGEST_JSON_SCHEMA}"""

        # Group by channel so LLM has per-channel context — more accurate than a flat list
        channels: dict[str, list[RawItem]] = {}
        for item in items:
            ch = item.metadata.get("channel", "unknown")
            channels.setdefault(ch, []).append(item)

        sections = []
        for ch, ch_items in channels.items():
            msgs = "\n".join(f"  - {item.text}" for item in ch_items)
            sections.append(f"#{ch} ({len(ch_items)} messages):\n{msgs}")

        content = "\n\n".join(sections)

        return f"""You are analyzing Slack workspace activity for {target_date.isoformat()}.

{len(items)} messages across {len(channels)} channel(s):

{content}

Extract a structured summary. Return ONLY valid JSON matching this schema:
{DIGEST_JSON_SCHEMA}

For source_specific include:
  "channel_breakdown": [{{"channel": "#name", "message_count": N, "key_topics": [...]}}]

Rules:
- highlights: top 5-10 most significant things
- key_decisions: only confirmed decisions, not proposals
- action_items: include owner name if @mentioned
- activity_level: low (<20 msgs), medium (20-100), high (>100)
"""
