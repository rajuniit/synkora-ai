from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.agent_pricing import AgentPricing
from src.models.agent_revenue import AgentRevenue, RevenueStatus
from src.models.credit_transaction import CreditTransaction
from src.models.tenant import Tenant
from src.services.billing.revenue_service import RevenueService


class TestRevenueService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db):
        return RevenueService(mock_db)

    async def test_get_revenue_by_id(self, service, mock_db):
        revenue_id = uuid4()
        mock_rev = MagicMock(spec=AgentRevenue)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rev
        mock_db.execute.return_value = mock_result

        result = await service.get_revenue_by_id(revenue_id)
        assert result == mock_rev
        mock_db.execute.assert_called_once()

    async def test_get_pending_payouts(self, service, mock_db):
        mock_row = MagicMock()
        mock_row.tenant_id = uuid4()
        mock_row.tenant_name = "Test Tenant"
        mock_row.total_pending_credits = 5000  # $100
        mock_row.transaction_count = 10
        mock_row.oldest_transaction = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        payouts = await service.get_pending_payouts()

        assert len(payouts) == 1
        assert payouts[0]["total_pending_amount"] == 100.0

    async def test_process_payout_no_pending(self, service, mock_db):
        tenant_id = uuid4()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.process_payout(tenant_id)
        assert result["success"] is False
        assert "No pending revenue" in result["message"]

    async def test_process_payout_below_threshold(self, service, mock_db):
        tenant_id = uuid4()
        mock_rev = MagicMock(creator_credits=100)  # $2.00
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_rev]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.process_payout(tenant_id)
        assert result["success"] is False
        assert "Minimum payout amount" in result["message"]

    async def test_process_payout_success_no_stripe(self, service, mock_db):
        tenant_id = uuid4()
        mock_rev = MagicMock(creator_credits=3000)  # $60.00
        mock_rev.status = RevenueStatus.PENDING
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_rev]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.process_payout(tenant_id)

        assert result["success"] is True
        assert result["amount"] == 60.0
        assert mock_rev.status == RevenueStatus.PAID
        assert mock_rev.payout_reference.startswith("PAYOUT-")
        mock_db.commit.assert_called_once()

    async def test_process_payout_stripe_success(self, service, mock_db):
        tenant_id = uuid4()
        mock_rev = MagicMock(creator_credits=3000)
        mock_rev.status = RevenueStatus.PENDING
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_rev]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("src.services.billing.revenue_service.StripeService") as MockStripeService:
            mock_stripe = AsyncMock()
            MockStripeService.create = AsyncMock(return_value=mock_stripe)
            mock_stripe.create_payout = AsyncMock(return_value={"success": True, "id": "tr_123"})

            result = await service.process_payout(tenant_id, stripe_account_id="acct_123")

            assert result["success"] is True
            assert result["payout_reference"] == "tr_123"
            mock_stripe.create_payout.assert_called_once_with(account_id="acct_123", amount=6000)

    async def test_process_payout_stripe_failure(self, service, mock_db):
        tenant_id = uuid4()
        mock_rev = MagicMock(creator_credits=3000)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_rev]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("src.services.billing.revenue_service.StripeService") as MockStripeService:
            mock_stripe = AsyncMock()
            MockStripeService.create = AsyncMock(return_value=mock_stripe)
            mock_stripe.create_payout = AsyncMock(return_value={"success": False, "error": "Failed"})

            result = await service.process_payout(tenant_id, stripe_account_id="acct_123")

            assert result["success"] is False
            assert "Stripe payout failed" in result["message"]

    async def test_get_revenue_analytics(self, service, mock_db):
        mock_summary = MagicMock()
        mock_summary.total_credits = 1000
        mock_summary.total_platform_credits = 300
        mock_summary.total_creator_credits = 700
        mock_summary.total_transactions = 20
        mock_summary.unique_customers = 5

        mock_daily_row = MagicMock()
        mock_daily_row.date = datetime.now(UTC).date()
        mock_daily_row.credits = 100
        mock_daily_row.creator_credits = 70
        mock_daily_row.transactions = 2

        mock_summary_result = MagicMock()
        mock_summary_result.first.return_value = mock_summary

        mock_daily_result = MagicMock()
        mock_daily_result.all.return_value = [mock_daily_row]

        mock_db.execute.side_effect = [mock_summary_result, mock_daily_result]

        analytics = await service.get_revenue_analytics()

        assert analytics["summary"]["total_revenue"] == 20.0  # 1000 * 0.02
        assert len(analytics["daily_breakdown"]) == 1

    async def test_get_top_customers(self, service, mock_db):
        mock_row = MagicMock()
        mock_row.tenant_id = uuid4()
        mock_row.tenant_name = "Customer 1"
        mock_row.total_credits = 500
        mock_row.transaction_count = 5

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        customers = await service.get_top_customers()

        assert len(customers) == 1
        assert customers[0]["total_revenue"] == 10.0  # 500 * 0.02

    async def test_get_payout_history(self, service, mock_db):
        mock_row = MagicMock()
        mock_row.payout_reference = "ref_123"
        mock_row.payout_date = datetime.now(UTC)
        mock_row.total_credits = 5000
        mock_row.transaction_count = 10

        mock_payout_result = MagicMock()
        mock_payout_result.all.return_value = [mock_row]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_db.execute.side_effect = [mock_payout_result, mock_count_result]

        history = await service.get_payout_history(uuid4())

        assert history["total_count"] == 1
        assert history["payouts"][0]["amount"] == 100.0

    async def test_mark_revenue_failed(self, service, mock_db):
        mock_rev = MagicMock(spec=AgentRevenue)
        with patch.object(service, "get_revenue_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_rev
            success = await service.mark_revenue_failed(uuid4(), "error")

            assert success is True
            assert mock_rev.status == RevenueStatus.FAILED
            assert mock_rev.notes == "error"
            mock_db.commit.assert_called_once()

    async def test_mark_revenue_failed_not_found(self, service, mock_db):
        with patch.object(service, "get_revenue_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            success = await service.mark_revenue_failed(uuid4(), "error")
            assert success is False
