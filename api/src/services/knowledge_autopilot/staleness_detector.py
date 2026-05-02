"""
Staleness Detector — Identifies wiki articles that may be outdated.

Compares article compilation timestamps against source document update timestamps
to compute a staleness score (0 = fresh, 1 = very stale).
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.wiki_article import WikiArticle

logger = logging.getLogger(__name__)


class StalenessDetector:
    """Detects and scores staleness for wiki articles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_staleness(self, knowledge_base_id: int) -> dict:
        """
        Recalculate staleness scores for all published articles in a KB.

        Staleness is based on time since last compilation relative to a 30-day window.
        Articles not compiled in 30+ days get score 1.0.
        """
        from src.models.document import Document, DocumentStatus

        result = await self.db.execute(
            select(WikiArticle).filter(
                WikiArticle.knowledge_base_id == knowledge_base_id,
                WikiArticle.status == "published",
            )
        )
        articles = result.scalars().all()

        if not articles:
            return {"updated": 0}

        # Get the latest SOURCE document update time for this KB.
        # Exclude wiki-type documents: they are regenerated on every compile, so including them
        # would cause circular staleness (compile → embed → updated_at=NOW → all articles stale).
        doc_result = await self.db.execute(
            select(Document.updated_at)
            .filter(
                Document.knowledge_base_id == knowledge_base_id,
                Document.status == DocumentStatus.COMPLETED,
                Document.source_type != "wiki",
            )
            .order_by(Document.updated_at.desc())
            .limit(1)
        )
        latest_doc_update = doc_result.scalar_one_or_none()

        now = datetime.now(UTC)
        max_age_seconds = 90 * 24 * 3600  # 90 days — avoids penalising stable content
        updated = 0

        for article in articles:
            compiled_at = article.last_compiled_at
            if not compiled_at:
                article.staleness_score = 1.0
                updated += 1
                continue

            # Time-based staleness
            age = (now - compiled_at).total_seconds()
            time_staleness = min(1.0, age / max_age_seconds)

            # Source-based staleness: if documents were updated after compilation
            source_staleness = 0.0
            if latest_doc_update and compiled_at < latest_doc_update:
                hours_behind = (latest_doc_update - compiled_at).total_seconds() / 3600
                source_staleness = min(1.0, hours_behind / (7 * 24))  # 7 days = fully stale

            # Combined score (source staleness weighted higher)
            article.staleness_score = round(min(1.0, source_staleness * 0.6 + time_staleness * 0.4), 2)
            updated += 1

        await self.db.commit()
        logger.info(f"Updated staleness for {updated} articles in KB {knowledge_base_id}")
        return {"updated": updated}
