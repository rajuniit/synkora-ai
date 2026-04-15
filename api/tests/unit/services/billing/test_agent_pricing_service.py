from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_pricing import AgentPricing, PricingModel
from src.services.billing.agent_pricing_service import AgentPricingService


class TestAgentPricingService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.close = AsyncMock()
        return session

    async def test_get_agent_pricing(self, mock_db):
        agent_id = uuid4()
        mock_pricing = MagicMock(spec=AgentPricing)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pricing
        mock_db.execute.return_value = mock_result

        result = await AgentPricingService.get_agent_pricing(agent_id, mock_db)

        assert result == mock_pricing
        mock_db.execute.assert_called_once()

    async def test_create_agent_pricing_success(self, mock_db):
        agent_id = uuid4()
        tenant_id = uuid4()

        # Mock get_agent_pricing to return None (no existing pricing)
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=None)):
            pricing = await AgentPricingService.create_agent_pricing(
                agent_id=agent_id, tenant_id=tenant_id, pricing_model=PricingModel.FREE, db=mock_db
            )

            assert pricing.agent_id == agent_id
            assert pricing.tenant_id == tenant_id
            assert pricing.pricing_model == PricingModel.FREE
            # is_monetized is a property now, not a field
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    async def test_create_agent_pricing_existing(self, mock_db):
        agent_id = uuid4()
        tenant_id = uuid4()

        # Mock get_agent_pricing to return existing pricing
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=MagicMock())):
            with pytest.raises(ValueError, match="already exists"):
                await AgentPricingService.create_agent_pricing(
                    agent_id=agent_id, tenant_id=tenant_id, pricing_model=PricingModel.FREE, db=mock_db
                )

    async def test_create_agent_pricing_per_use_validation(self, mock_db):
        agent_id = uuid4()
        tenant_id = uuid4()
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="positive credit cost"):
                await AgentPricingService.create_agent_pricing(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    pricing_model=PricingModel.PER_USE,
                    credits_per_use=0,
                    db=mock_db,
                )

    async def test_create_agent_pricing_subscription_validation(self, mock_db):
        agent_id = uuid4()
        tenant_id = uuid4()
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="monthly credit cost"):
                await AgentPricingService.create_agent_pricing(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    pricing_model=PricingModel.SUBSCRIPTION,
                    monthly_subscription_credits=None,
                    db=mock_db,
                )

    async def test_update_agent_pricing(self, mock_db):
        agent_id = uuid4()
        mock_pricing = MagicMock(spec=AgentPricing)

        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=mock_pricing)):
            await AgentPricingService.update_agent_pricing(agent_id=agent_id, credits_per_use=10, db=mock_db)

            assert mock_pricing.credits_per_use == 10
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_pricing)

    async def test_update_agent_pricing_not_found(self, mock_db):
        agent_id = uuid4()
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="not found"):
                await AgentPricingService.update_agent_pricing(agent_id=agent_id, credits_per_use=10, db=mock_db)

    async def test_calculate_agent_cost_free(self, mock_db):
        agent_id = uuid4()
        mock_pricing = MagicMock(spec=AgentPricing)
        mock_pricing.pricing_model = PricingModel.FREE
        # Mock is_free property behavior
        type(mock_pricing).is_free = pytest.fixture(lambda self: self.pricing_model == PricingModel.FREE)
        mock_pricing.is_free = True
        mock_pricing.is_active = True

        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=mock_pricing)):
            cost = await AgentPricingService.calculate_agent_cost(agent_id, 5, mock_db)
            assert cost == 5

    async def test_calculate_agent_cost_per_use(self, mock_db):
        agent_id = uuid4()
        mock_pricing = MagicMock(spec=AgentPricing)
        mock_pricing.pricing_model = PricingModel.PER_USE
        mock_pricing.credits_per_use = 10
        mock_pricing.is_free = False
        mock_pricing.is_active = True

        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=mock_pricing)):
            cost = await AgentPricingService.calculate_agent_cost(agent_id, 5, mock_db)
            assert cost == 15  # 5 + 10

    async def test_record_agent_usage_not_monetized(self, mock_db):
        agent_id = uuid4()
        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=None)):
            result = await AgentPricingService.record_agent_usage(
                agent_id=agent_id, transaction_id=uuid4(), credits_used=10, db=mock_db
            )
            assert result is None

    async def test_record_agent_usage_success(self, mock_db):
        agent_id = uuid4()
        tenant_id = uuid4()
        mock_pricing = MagicMock(spec=AgentPricing)
        mock_pricing.id = uuid4()
        mock_pricing.tenant_id = tenant_id
        mock_pricing.pricing_model = PricingModel.PER_USE
        mock_pricing.is_paid = True
        mock_pricing.revenue_share_percentage = Decimal("70.00")
        mock_pricing.total_uses = 0
        mock_pricing.total_revenue_credits = 0

        with patch.object(AgentPricingService, "get_agent_pricing", AsyncMock(return_value=mock_pricing)):
            revenue = await AgentPricingService.record_agent_usage(
                agent_id=agent_id, transaction_id=uuid4(), credits_used=100, db=mock_db
            )

            assert revenue is not None
            assert revenue.total_credits == 100
            # Creator credits: 100 * 0.70 = 70
            assert revenue.creator_credits == 70
            # Platform credits: 100 - 70 = 30
            assert revenue.platform_credits == 30
            assert revenue.agent_pricing_id == mock_pricing.id
            assert revenue.tenant_id == tenant_id

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

            assert mock_pricing.total_uses == 1
            assert mock_pricing.total_revenue_credits == 70

    async def test_get_agent_earnings(self, mock_db):
        agent_id = uuid4()

        mock_row = MagicMock()
        mock_row.total_credits = 5000
        mock_row.total_platform_credits = 1500
        mock_row.total_creator_credits = 3500
        mock_row.total_transactions = 50

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result

        earnings = await AgentPricingService.get_agent_earnings(agent_id, db=mock_db)

        assert earnings["total_credits"] == 5000
        assert earnings["creator_credits"] == 3500
        assert earnings["total_transactions"] == 50
        # USD value check (3500 * 0.02 = 70.0)
        assert earnings["creator_earnings_usd"] == 70.0

    async def test_get_creator_earnings(self, mock_db):
        creator_tenant_id = uuid4()

        mock_row = MagicMock()
        mock_row.total_credits = 10000
        mock_row.total_platform_credits = 3000
        mock_row.total_creator_credits = 7000
        mock_row.monetized_agents = 2
        mock_row.total_transactions = 100

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row

        # Second query for pending payout
        mock_pending_result = MagicMock()
        mock_pending_result.scalar.return_value = 2500  # credits

        mock_db.execute.side_effect = [mock_result, mock_pending_result]

        earnings = await AgentPricingService.get_creator_earnings(creator_tenant_id, db=mock_db)

        assert earnings["creator_credits"] == 7000
        assert earnings["pending_payout_credits"] == 2500
        assert earnings["monetized_agents"] == 2
        # USD check (7000 * 0.02 = 140.0)
        assert earnings["creator_earnings_usd"] == 140.0

    async def test_get_top_earning_agents(self, mock_db):
        mock_row1 = MagicMock(
            agent_id=uuid4(),
            agent_name="Agent 1",
            total_revenue_credits=5000,
            creator_earnings_credits=3500,
            usage_count=50,
        )
        mock_row2 = MagicMock(
            agent_id=uuid4(),
            agent_name="Agent 2",
            total_revenue_credits=2500,
            creator_earnings_credits=1750,
            usage_count=25,
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        agents = await AgentPricingService.get_top_earning_agents(limit=2, db=mock_db)

        assert len(agents) == 2
        assert agents[0]["agent_name"] == "Agent 1"
        assert agents[0]["creator_earnings_credits"] == 3500
        assert agents[0]["creator_earnings_usd"] == 70.0

        assert agents[1]["agent_name"] == "Agent 2"
