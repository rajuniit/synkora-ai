from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.credit_balance import CreditBalance
from src.models.credit_transaction import ActionType as ActionTypeEnum
from src.models.credit_transaction import CreditTransaction, TransactionType
from src.services.billing.credit_service import CreditService


class TestCreditService:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_db):
        return CreditService(mock_db)

    @pytest.fixture
    def mock_balance(self):
        """Create a real CreditBalance object for testing instead of MagicMock."""
        balance = CreditBalance(tenant_id=uuid4(), total_credits=100, used_credits=20, available_credits=80)
        balance.id = uuid4()
        return balance

    def _setup_db_execute_mock(self, mock_db, return_value):
        """Helper to setup db.execute().scalar_one_or_none() mock."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = return_value
        mock_db.execute.return_value = mock_result
        return mock_result

    async def test_get_balance(self, service, mock_db, mock_balance):
        self._setup_db_execute_mock(mock_db, mock_balance)

        result = await service.get_balance(mock_balance.tenant_id)
        assert result == mock_balance
        mock_db.execute.assert_called_once()

    async def test_get_or_create_balance_existing(self, service, mock_db, mock_balance):
        with patch.object(service, "get_balance", AsyncMock(return_value=mock_balance)):
            result = await service.get_or_create_balance(mock_balance.tenant_id)
            assert result == mock_balance
            mock_db.add.assert_not_called()

    async def test_get_or_create_balance_new(self, service, mock_db):
        tenant_id = uuid4()
        with patch.object(service, "get_balance", AsyncMock(return_value=None)):
            balance = await service.get_or_create_balance(tenant_id)

            assert balance.tenant_id == tenant_id
            assert balance.total_credits == 0
            assert balance.available_credits == 0
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    async def test_get_available_credits(self, service, mock_balance):
        with patch.object(service, "get_balance", AsyncMock(return_value=mock_balance)):
            result = await service.get_available_credits(mock_balance.tenant_id)
            assert result == 80

    async def test_get_available_credits_no_balance(self, service):
        with patch.object(service, "get_balance", AsyncMock(return_value=None)):
            result = await service.get_available_credits(uuid4())
            assert result == 0

    async def test_add_credits(self, service, mock_db, mock_balance):
        """Test adding credits to a balance."""
        tenant_id = uuid4()
        mock_balance.tenant_id = tenant_id
        mock_balance.total_credits = 100
        mock_balance.used_credits = 20
        mock_balance.available_credits = 80

        # Mock db.execute().scalar_one_or_none() to return balance
        self._setup_db_execute_mock(mock_db, mock_balance)

        transaction = await service.add_credits(
            tenant_id=tenant_id,
            amount=50,
            transaction_type=TransactionType.PURCHASE,
            description="Purchase",
            reference_id=uuid4(),
            reference_type="payment",
        )

        # Verify balance was updated
        assert mock_balance.total_credits == 150  # 100 + 50
        assert mock_balance.available_credits == 130  # 150 - 20

        # Verify transaction
        assert transaction.amount == 50
        assert transaction.transaction_type == TransactionType.PURCHASE
        assert transaction.balance_after == 130

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_deduct_credits_success(self, service, mock_db, mock_balance):
        """Test deducting credits successfully."""
        tenant_id = uuid4()
        mock_balance.tenant_id = tenant_id
        mock_balance.available_credits = 100
        mock_balance.total_credits = 100
        mock_balance.used_credits = 0

        self._setup_db_execute_mock(mock_db, mock_balance)

        transaction = await service.deduct_credits(
            tenant_id=tenant_id, amount=10, transaction_type=TransactionType.USAGE, description="Usage"
        )

        assert mock_balance.used_credits == 10
        assert mock_balance.available_credits == 90

        assert transaction.amount == -10
        assert transaction.balance_after == 90

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_deduct_credits_insufficient(self, service, mock_db, mock_balance):
        """Test deducting credits with insufficient balance."""
        mock_balance.available_credits = 5
        mock_balance.total_credits = 5
        mock_balance.used_credits = 0

        self._setup_db_execute_mock(mock_db, mock_balance)

        with pytest.raises(ValueError, match="Insufficient credits"):
            await service.deduct_credits(
                tenant_id=uuid4(), amount=10, transaction_type=TransactionType.USAGE, description="Usage"
            )

    async def test_refund_credits(self, service, mock_db, mock_balance):
        """Test refunding credits."""
        tenant_id = uuid4()
        mock_balance.tenant_id = tenant_id
        mock_balance.used_credits = 50
        mock_balance.total_credits = 100
        mock_balance.available_credits = 50

        self._setup_db_execute_mock(mock_db, mock_balance)

        transaction = await service.refund_credits(tenant_id=tenant_id, amount=20, description="Refund")

        assert mock_balance.used_credits == 30  # 50 - 20
        assert mock_balance.available_credits == 70  # 100 - 30

        assert transaction.amount == 20
        assert transaction.transaction_type == TransactionType.REFUND
        assert transaction.balance_after == 70

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_get_transaction_history(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        mock_db.execute.return_value = mock_result

        history = await service.get_transaction_history(uuid4())
        assert len(history) == 2
        mock_db.execute.assert_called_once()

    async def test_get_transaction_history_filters(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_transaction_history(uuid4(), filters={"transaction_type": TransactionType.USAGE})
        mock_db.execute.assert_called_once()

    async def test_get_usage_stats(self, service, mock_balance):
        with patch.object(service, "get_balance", AsyncMock(return_value=mock_balance)):
            stats = await service.get_usage_stats(mock_balance.tenant_id)

            assert stats["total_credits"] == 100
            assert stats["used_credits"] == 20
            assert stats["available_credits"] == 80
            assert stats["usage_percentage"] == 20.0

    async def test_get_usage_stats_no_balance(self, service):
        with patch.object(service, "get_balance", AsyncMock(return_value=None)):
            stats = await service.get_usage_stats(uuid4())
            assert stats["total_credits"] == 0

    async def test_reset_monthly_usage(self, service, mock_db, mock_balance):
        """Test resetting monthly usage."""
        mock_balance.used_credits = 50
        mock_balance.total_credits = 100
        mock_balance.available_credits = 50

        self._setup_db_execute_mock(mock_db, mock_balance)

        await service.reset_monthly_usage(mock_balance.tenant_id)

        assert mock_balance.used_credits == 0
        assert mock_balance.available_credits == 100
        mock_db.commit.assert_called_once()

    async def test_deduct_credits_idempotent_success(self, service, mock_db, mock_balance):
        """Test idempotent credit deduction."""
        tenant_id = uuid4()
        mock_balance.tenant_id = tenant_id
        mock_balance.available_credits = 100
        mock_balance.total_credits = 100
        mock_balance.used_credits = 0

        # Setup mock to return:
        # 1st call (get balance with lock): return mock_balance
        # 2nd call (check idempotency): return None (no existing transaction)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_balance, None]
        mock_db.execute.return_value = mock_result

        with patch("src.models.credit_transaction.ActionType.get_credit_cost", return_value=10):
            transaction = await service.deduct_credits_idempotent(
                tenant_id=tenant_id,
                user_id=None,
                agent_id=uuid4(),
                action_type=ActionTypeEnum.AGENT_EXECUTION,
                metadata={"message_id": "msg_123"},
            )

            assert transaction is not None
            assert transaction.amount == -10
            assert transaction.idempotency_key == "msg_msg_123"

            mock_db.add.assert_called()
            mock_db.commit.assert_called()

    async def test_deduct_credits_idempotent_duplicate(self, service, mock_db, mock_balance):
        """Test idempotent deduction returns None for duplicates."""
        # Setup mock to return:
        # 1st call (get balance with lock): return mock_balance
        # 2nd call (check idempotency): return existing transaction (duplicate)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_balance, MagicMock()]  # Existing transaction
        mock_db.execute.return_value = mock_result

        with patch("src.models.credit_transaction.ActionType.get_credit_cost", return_value=10):
            result = await service.deduct_credits_idempotent(
                tenant_id=uuid4(),
                user_id=None,
                agent_id=uuid4(),
                action_type=ActionTypeEnum.AGENT_EXECUTION,
                metadata={"message_id": "msg_123"},
            )

            assert result is None

    async def test_deduct_credits_idempotent_insufficient(self, service, mock_db, mock_balance):
        """Test idempotent deduction with insufficient balance."""
        mock_balance.available_credits = 0
        mock_balance.total_credits = 0
        mock_balance.used_credits = 0

        # Setup mock to return:
        # 1st call (get balance with lock): return mock_balance with 0 credits
        # 2nd call (check idempotency): return None (no existing transaction)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_balance, None]
        mock_db.execute.return_value = mock_result

        with patch("src.models.credit_transaction.ActionType.get_credit_cost", return_value=10):
            result = await service.deduct_credits_idempotent(
                tenant_id=uuid4(),
                user_id=None,
                agent_id=uuid4(),
                action_type=ActionTypeEnum.AGENT_EXECUTION,
                metadata={"message_id": "msg_123"},
            )

            # Should return None due to insufficient credits
            assert result is None
