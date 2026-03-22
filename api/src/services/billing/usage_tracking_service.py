"""
Usage Tracking Service

Tracks and analyzes credit usage across the platform for analytics and reporting.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.credit_transaction import CreditTransaction, TransactionType
from src.models.usage_analytics import UsageAnalytics

logger = logging.getLogger(__name__)

# Redis key prefix for buffered usage counters.
# Key format: usage:{tenant_id}:{agent_id_or_none}:{metric_type}:{YYYY-MM-DD}
# Hash fields: "count" (int), "credits" (int)
USAGE_REDIS_PREFIX = "usage:"


def _to_date(value: datetime | date) -> date:
    """Convert datetime or date to date object."""
    if isinstance(value, datetime):
        return value.date()
    return value


def record_usage_buffered(
    tenant_id: UUID,
    metric_type: str,
    count: int = 1,
    credits: int = 0,
    agent_id: UUID | None = None,
    analytics_date: date | None = None,
) -> None:
    """
    Increment usage counters in Redis without touching the database.

    This is the hot-path writer. The actual DB upsert is handled by the
    flush_usage_analytics Celery task which runs every 60 seconds.

    A 2-day TTL is set on every key so counters self-clean if the flush
    task is down for an extended period.

    Args:
        tenant_id: Tenant UUID
        metric_type: Metric name (e.g. 'chat_messages', 'api_calls')
        count: Number of events to add
        credits: Credits consumed to add
        agent_id: Agent UUID (None for tenant-wide metrics)
        analytics_date: Date bucket (defaults to today UTC)
    """
    from src.config.redis import get_redis

    if analytics_date is None:
        analytics_date = datetime.now(UTC).date()

    agent_part = str(agent_id) if agent_id else "none"
    key = f"{USAGE_REDIS_PREFIX}{tenant_id}:{agent_part}:{metric_type}:{analytics_date.isoformat()}"

    try:
        redis = get_redis()
        pipe = redis.pipeline()
        pipe.hincrby(key, "count", count)
        pipe.hincrby(key, "credits", credits)
        pipe.expire(key, 172800)  # 2-day TTL safety net
        pipe.execute()
    except Exception as e:
        # Analytics loss is acceptable — do not propagate errors to the hot path.
        logger.warning(f"Failed to buffer usage in Redis (analytics may be delayed): {e}")


class UsageTrackingService:
    """Service for tracking and analyzing credit usage"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_usage(
        self,
        tenant_id: UUID,
        metric_type: str,
        count: int = 1,
        credits: int = 0,
        agent_id: UUID | None = None,
        date: datetime | date | None = None,
    ) -> None:
        """
        Buffer a usage increment in Redis.

        The DB write is deferred to the flush_usage_analytics Celery task
        (runs every 60 seconds), so this method is non-blocking and does
        not hold a DB connection.

        Args:
            tenant_id: Tenant UUID
            metric_type: Metric name (e.g. 'chat_messages', 'api_calls')
            count: Number of events to add
            credits: Credits consumed to add
            agent_id: Agent UUID (None for tenant-wide metrics)
            date: Date bucket (defaults to today UTC)
        """
        analytics_date = _to_date(date) if date is not None else None
        record_usage_buffered(
            tenant_id=tenant_id,
            metric_type=metric_type,
            count=count,
            credits=credits,
            agent_id=agent_id,
            analytics_date=analytics_date,
        )

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        agent_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Get usage summary for a period

        Args:
            tenant_id: Tenant UUID
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)
            agent_id: Filter by agent (optional)

        Returns:
            dict: Usage summary
        """
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Get total interactions and credits
        query = select(
            func.sum(UsageAnalytics.total_count).label("total_interactions"),
            func.sum(UsageAnalytics.credits_consumed).label("total_credits"),
        ).where(
            and_(
                UsageAnalytics.tenant_id == tenant_id,
                UsageAnalytics.date >= _to_date(start_date),
                UsageAnalytics.date <= _to_date(end_date),
            )
        )

        if agent_id:
            query = query.where(UsageAnalytics.agent_id == agent_id)

        result = await self.db.execute(query)
        stats = result.first()

        # Get breakdown by metric type
        breakdown_query = (
            select(UsageAnalytics.metric_type, func.sum(UsageAnalytics.total_count).label("count"))
            .where(
                and_(
                    UsageAnalytics.tenant_id == tenant_id,
                    UsageAnalytics.date >= _to_date(start_date),
                    UsageAnalytics.date <= _to_date(end_date),
                )
            )
            .group_by(UsageAnalytics.metric_type)
        )

        if agent_id:
            breakdown_query = breakdown_query.where(UsageAnalytics.agent_id == agent_id)

        breakdown_result = await self.db.execute(breakdown_query)
        breakdown_data = breakdown_result.all()

        breakdown = {row.metric_type: int(row.count or 0) for row in breakdown_data}

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
            "total_interactions": int(stats.total_interactions or 0) if stats else 0,
            "total_credits_used": int(stats.total_credits or 0) if stats else 0,
            "breakdown": {
                "chat_messages": breakdown.get("chat_messages", 0),
                "file_uploads": breakdown.get("file_uploads", 0),
                "api_calls": breakdown.get("api_calls", 0),
            },
        }

    async def get_daily_usage_trend(
        self, tenant_id: UUID, days: int = 30, agent_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """
        Get daily usage trend

        Args:
            tenant_id: Tenant UUID
            days: Number of days to retrieve
            agent_id: Filter by agent (optional)

        Returns:
            list: Daily usage data
        """
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days)

        query = (
            select(
                UsageAnalytics.date,
                func.sum(UsageAnalytics.total_count).label("total_count"),
                func.sum(UsageAnalytics.credits_consumed).label("credits_consumed"),
            )
            .where(
                and_(
                    UsageAnalytics.tenant_id == tenant_id,
                    UsageAnalytics.date >= start_date,
                    UsageAnalytics.date <= end_date,
                )
            )
            .group_by(UsageAnalytics.date)
            .order_by(UsageAnalytics.date)
        )

        if agent_id:
            query = query.where(UsageAnalytics.agent_id == agent_id)

        result = await self.db.execute(query)
        daily_data = result.all()

        return [
            {
                "date": row.date.isoformat(),
                "total_interactions": int(row.total_count or 0),
                "total_credits_used": int(row.credits_consumed or 0),
            }
            for row in daily_data
        ]

    async def get_agent_usage_breakdown(
        self, tenant_id: UUID, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Get usage breakdown by agent

        Args:
            tenant_id: Tenant UUID
            start_date: Start date
            end_date: End date

        Returns:
            list: Agent usage breakdown
        """
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        query = (
            select(
                UsageAnalytics.agent_id,
                Agent.agent_name,
                func.sum(UsageAnalytics.total_count).label("total_interactions"),
                func.sum(UsageAnalytics.credits_consumed).label("total_credits"),
            )
            .join(Agent, UsageAnalytics.agent_id == Agent.id)
            .where(
                and_(
                    UsageAnalytics.tenant_id == tenant_id,
                    UsageAnalytics.agent_id.isnot(None),
                    UsageAnalytics.date >= _to_date(start_date),
                    UsageAnalytics.date <= _to_date(end_date),
                )
            )
            .group_by(UsageAnalytics.agent_id, Agent.agent_name)
            .order_by(func.sum(UsageAnalytics.credits_consumed).desc())
        )

        result = await self.db.execute(query)
        agents = result.all()

        return [
            {
                "agent_id": str(agent.agent_id),
                "agent_name": agent.agent_name,
                "total_interactions": int(agent.total_interactions or 0),
                "total_credits_used": int(agent.total_credits or 0),
            }
            for agent in agents
        ]

    async def get_action_type_breakdown(
        self, tenant_id: UUID, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, int]:
        """
        Get usage breakdown by action type

        Args:
            tenant_id: Tenant UUID
            start_date: Start date
            end_date: End date

        Returns:
            dict: Action type breakdown
        """
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        query = (
            select(
                CreditTransaction.reference_type,
                func.count(CreditTransaction.id).label("count"),
                func.sum(func.abs(CreditTransaction.amount)).label("total_credits"),
            )
            .where(
                and_(
                    CreditTransaction.tenant_id == tenant_id,
                    CreditTransaction.transaction_type == TransactionType.USAGE,
                    CreditTransaction.created_at >= start_date,
                    CreditTransaction.created_at <= end_date,
                )
            )
            .group_by(CreditTransaction.reference_type)
        )

        result = await self.db.execute(query)
        breakdown = result.all()

        return {
            action.reference_type if action.reference_type else "unknown": {
                "count": int(action.count or 0),
                "total_credits": int(action.total_credits or 0),
            }
            for action in breakdown
        }

    async def get_peak_usage_times(self, tenant_id: UUID, days: int = 7) -> dict[str, Any]:
        """
        Get peak usage times analysis

        Args:
            tenant_id: Tenant UUID
            days: Number of days to analyze

        Returns:
            dict: Peak usage analysis
        """
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=days)

        query = (
            select(
                func.extract("hour", CreditTransaction.created_at).label("hour"),
                func.count(CreditTransaction.id).label("count"),
            )
            .where(
                and_(
                    CreditTransaction.tenant_id == tenant_id,
                    CreditTransaction.created_at >= start_date,
                    CreditTransaction.created_at <= end_date,
                )
            )
            .group_by(func.extract("hour", CreditTransaction.created_at))
            .order_by(func.count(CreditTransaction.id).desc())
        )

        result = await self.db.execute(query)
        hours = result.fetchall()

        hourly_distribution = {int(h.hour): int(h.count) for h in hours}
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 0

        return {"peak_hour": peak_hour, "hourly_distribution": hourly_distribution, "analysis_period_days": days}

    async def export_usage_report(
        self,
        tenant_id: UUID,
        start_date: datetime | date | None = None,
        end_date: datetime | date | None = None,
        format: str = "json",
    ) -> dict[str, Any]:
        """
        Export comprehensive usage report

        Args:
            tenant_id: Tenant UUID
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)
            format: Export format (json, csv)

        Returns:
            dict: Complete usage report
        """
        # Set defaults for None values
        if end_date is None:
            end_date = datetime.now(UTC)
        if start_date is None:
            start_date = (
                end_date - timedelta(days=30)
                if isinstance(end_date, datetime)
                else datetime.combine(end_date, datetime.min.time()) - timedelta(days=30)
            )

        # Calculate days for daily trend
        start_dt = start_date if isinstance(start_date, datetime) else datetime.combine(start_date, datetime.min.time())
        end_dt = end_date if isinstance(end_date, datetime) else datetime.combine(end_date, datetime.min.time())
        days = (end_dt - start_dt).days or 30

        summary = await self.get_usage_summary(tenant_id, start_date, end_date)
        daily_trend = await self.get_daily_usage_trend(tenant_id, days=days)
        agent_breakdown = await self.get_agent_usage_breakdown(tenant_id, start_date, end_date)
        action_breakdown = await self.get_action_type_breakdown(tenant_id, start_date, end_date)

        # Format dates for output
        start_iso = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
        end_iso = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)

        return {
            "report_metadata": {
                "tenant_id": str(tenant_id),
                "generated_at": datetime.now(UTC).isoformat(),
                "period": {"start_date": start_iso, "end_date": end_iso},
                "format": format,
            },
            "summary": summary,
            "daily_trend": daily_trend,
            "agent_breakdown": agent_breakdown,
            "action_type_breakdown": action_breakdown,
        }
