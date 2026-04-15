from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.billing.usage_tracking_service import UsageTrackingService


class TestUsageTrackingService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db):
        return UsageTrackingService(mock_db)

    @pytest.mark.asyncio
    async def test_record_usage(self, service, mock_db):
        """record_usage buffers to Redis and returns None (DB write is deferred to Celery)."""
        tenant_id = uuid4()
        agent_id = uuid4()
        metric_type = "chat_messages"
        count = 5
        credits = 10

        with patch("src.services.billing.usage_tracking_service.record_usage_buffered") as mock_buffered:
            result = await service.record_usage(
                tenant_id=tenant_id, metric_type=metric_type, count=count, credits=credits, agent_id=agent_id
            )

            assert result is None
            mock_buffered.assert_called_once_with(
                tenant_id=tenant_id,
                metric_type=metric_type,
                count=count,
                credits=credits,
                agent_id=agent_id,
                analytics_date=None,
            )
            # No DB operations — those are deferred to the flush_usage_analytics task.
            mock_db.commit.assert_not_called()
            mock_db.refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_usage_summary(self, service, mock_db):
        tenant_id = uuid4()

        mock_stats = MagicMock()
        mock_stats.total_interactions = 100
        mock_stats.total_credits = 500

        mock_breakdown_row = MagicMock()
        mock_breakdown_row.metric_type = "chat_messages"
        mock_breakdown_row.count = 80

        mock_db.execute.side_effect = [MagicMock(first=lambda: mock_stats), MagicMock(all=lambda: [mock_breakdown_row])]

        summary = await service.get_usage_summary(tenant_id)

        assert summary["total_interactions"] == 100
        assert summary["total_credits_used"] == 500
        assert summary["breakdown"]["chat_messages"] == 80

    @pytest.mark.asyncio
    async def test_get_daily_usage_trend(self, service, mock_db):
        tenant_id = uuid4()

        mock_row = MagicMock()
        mock_row.date = datetime.now(UTC).date()
        mock_row.total_count = 10
        mock_row.credits_consumed = 50

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        trend = await service.get_daily_usage_trend(tenant_id)

        assert len(trend) == 1
        assert trend[0]["total_interactions"] == 10
        assert trend[0]["total_credits_used"] == 50

    @pytest.mark.asyncio
    async def test_get_agent_usage_breakdown(self, service, mock_db):
        tenant_id = uuid4()

        mock_agent = MagicMock()
        mock_agent.agent_id = uuid4()
        mock_agent.agent_name = "Agent 1"
        mock_agent.total_interactions = 20
        mock_agent.total_credits = 100

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_agent]
        mock_db.execute.return_value = mock_result

        breakdown = await service.get_agent_usage_breakdown(tenant_id)

        assert len(breakdown) == 1
        assert breakdown[0]["agent_name"] == "Agent 1"

    @pytest.mark.asyncio
    async def test_get_action_type_breakdown(self, service, mock_db):
        tenant_id = uuid4()

        mock_row = MagicMock()
        mock_row.reference_type = "agent"
        mock_row.count = 50
        mock_row.total_credits = 200

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        breakdown = await service.get_action_type_breakdown(tenant_id)

        assert "agent" in breakdown
        assert breakdown["agent"]["count"] == 50

    @pytest.mark.asyncio
    async def test_get_peak_usage_times(self, service, mock_db):
        tenant_id = uuid4()

        mock_row = MagicMock()
        mock_row.hour = 14.0  # 2 PM
        mock_row.count = 100

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        result = await service.get_peak_usage_times(tenant_id)

        assert result["peak_hour"] == 14
        assert result["hourly_distribution"][14] == 100

    @pytest.mark.asyncio
    async def test_export_usage_report(self, service):
        tenant_id = uuid4()
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)

        # Mock internal methods
        with (
            patch.object(service, "get_usage_summary", new_callable=AsyncMock) as mock_summary,
            patch.object(service, "get_daily_usage_trend", new_callable=AsyncMock) as mock_trend,
            patch.object(service, "get_agent_usage_breakdown", new_callable=AsyncMock) as mock_agent_bd,
            patch.object(service, "get_action_type_breakdown", new_callable=AsyncMock) as mock_action_bd,
        ):
            mock_summary.return_value = {"total_interactions": 10}
            mock_trend.return_value = []
            mock_agent_bd.return_value = []
            mock_action_bd.return_value = {}

            report = await service.export_usage_report(tenant_id, start_date, end_date)

            assert report["report_metadata"]["tenant_id"] == str(tenant_id)
            assert report["summary"]["total_interactions"] == 10

            mock_summary.assert_called_once()
            mock_trend.assert_called_once()
            mock_agent_bd.assert_called_once()
            mock_action_bd.assert_called_once()
