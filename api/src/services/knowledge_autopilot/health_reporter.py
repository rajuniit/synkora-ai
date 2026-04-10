"""
Health Reporter — Generates knowledge base health statistics.

Aggregates article counts, staleness distribution, category coverage,
and compilation history into a health report.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.wiki_article import WikiArticle, WikiCompilationJob

logger = logging.getLogger(__name__)


class HealthReporter:
    """Generates health reports for a knowledge base's wiki."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self, knowledge_base_id: str, tenant_id: str) -> dict:
        """Generate a comprehensive health report for a knowledge base wiki."""

        # Article stats
        stats_result = await self.db.execute(
            select(
                func.count(WikiArticle.id),
                func.avg(WikiArticle.staleness_score),
                func.min(WikiArticle.staleness_score),
                func.max(WikiArticle.staleness_score),
            ).filter(
                WikiArticle.knowledge_base_id == knowledge_base_id,
                WikiArticle.tenant_id == tenant_id,
                WikiArticle.status == "published",
            )
        )
        row = stats_result.one()
        total = row[0] or 0
        avg_staleness = float(row[1] or 0)
        min_staleness = float(row[2] or 0)
        max_staleness = float(row[3] or 0)

        # Category distribution
        cat_result = await self.db.execute(
            select(WikiArticle.category, func.count(WikiArticle.id))
            .filter(
                WikiArticle.knowledge_base_id == knowledge_base_id,
                WikiArticle.tenant_id == tenant_id,
                WikiArticle.status == "published",
            )
            .group_by(WikiArticle.category)
        )
        categories = dict(cat_result.all())

        # Staleness distribution
        now = datetime.now(UTC)
        fresh_result = await self.db.execute(
            select(func.count(WikiArticle.id)).filter(
                WikiArticle.knowledge_base_id == knowledge_base_id,
                WikiArticle.tenant_id == tenant_id,
                WikiArticle.status == "published",
                WikiArticle.staleness_score < 0.3,
            )
        )
        fresh_count = fresh_result.scalar() or 0

        stale_result = await self.db.execute(
            select(func.count(WikiArticle.id)).filter(
                WikiArticle.knowledge_base_id == knowledge_base_id,
                WikiArticle.tenant_id == tenant_id,
                WikiArticle.status == "published",
                WikiArticle.staleness_score > 0.7,
            )
        )
        stale_count = stale_result.scalar() or 0

        # Recent compilations (last 7 days)
        week_ago = now - timedelta(days=7)
        comp_result = await self.db.execute(
            select(func.count(WikiCompilationJob.id)).filter(
                WikiCompilationJob.knowledge_base_id == knowledge_base_id,
                WikiCompilationJob.tenant_id == tenant_id,
                WikiCompilationJob.created_at >= week_ago,
            )
        )
        recent_compilations = comp_result.scalar() or 0

        health_score = max(0.0, min(1.0, 1.0 - avg_staleness))

        return {
            "knowledge_base_id": knowledge_base_id,
            "generated_at": now.isoformat(),
            "health_score": round(health_score, 2),
            "total_articles": total,
            "avg_staleness": round(avg_staleness, 2),
            "min_staleness": round(min_staleness, 2),
            "max_staleness": round(max_staleness, 2),
            "categories": categories,
            "freshness_distribution": {
                "fresh": fresh_count,
                "moderate": total - fresh_count - stale_count,
                "stale": stale_count,
            },
            "recent_compilations_7d": recent_compilations,
        }
