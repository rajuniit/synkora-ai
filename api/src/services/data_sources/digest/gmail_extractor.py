"""Gmail daily digest extractor."""

import logging
from datetime import date as DateType
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base import DIGEST_JSON_SCHEMA, BaseDigestExtractor, RawItem

logger = logging.getLogger(__name__)


class GmailDigestExtractor(BaseDigestExtractor):
    """Extracts daily digest from a Gmail data source."""

    @property
    def source_type(self) -> str:
        return "GMAIL"

    async def fetch_items(
        self,
        data_source: DataSource,
        start: datetime,
        end: datetime,
        db: AsyncSession,
    ) -> list[RawItem]:
        from src.services.data_sources.gmail_connector import GmailConnector

        connector = GmailConnector(data_source, db)
        connected = await connector.connect()
        if not connected:
            logger.warning(f"Could not connect to Gmail data source {data_source.id}")
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

            if ts and not (start <= ts < end):
                continue

            meta = doc.get("metadata", {})
            subject = meta.get("subject", "(no subject)")
            sender = meta.get("from", "unknown")
            label = f"[From: {sender}] [{subject}] "
            text = doc.get("text", "")[:500]  # trim body to avoid token explosion
            items.append(RawItem(text=f"{label}{text}", metadata=meta))

        return items

    def build_prompt(self, items: list[RawItem], target_date: DateType) -> str:
        content = "\n".join(f"- {item.text}" for item in items)
        if not content:
            content = "(no emails)"
        return f"""You are analyzing Gmail inbox activity for {target_date.isoformat()}.

Emails ({len(items)} total):
{content}

Extract a structured summary. Return ONLY valid JSON matching this schema:
{DIGEST_JSON_SCHEMA}

For source_specific include:
  "top_senders": ["name/email", ...],
  "label_breakdown": [{{"label": "name", "count": N}}],
  "threads_requiring_reply": ["subject", ...]

Rules:
- highlights: most important emails/threads
- key_decisions: any confirmed commitments found in emails
- action_items: follow-ups or tasks mentioned in emails
- activity_level: low (<10), medium (10-50), high (>50)
"""
