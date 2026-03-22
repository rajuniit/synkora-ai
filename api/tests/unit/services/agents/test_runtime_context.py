import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agents.runtime_context import (
    RuntimeContext,
    _authenticated_clients,
    _runtime_context,
    clear_authenticated_client,
    get_authenticated_client,
    get_runtime_context,
    set_authenticated_client,
)


class TestRuntimeContext:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def context_data(self, mock_db_session):
        return {
            "tenant_id": uuid.uuid4(),
            "agent_id": uuid.uuid4(),
            "db_session": mock_db_session,
            "llm_client": MagicMock(),
            "conversation_id": uuid.uuid4(),
            "message_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
        }

    def test_runtime_context_init(self, context_data):
        ctx = RuntimeContext(**context_data)
        assert ctx.tenant_id == context_data["tenant_id"]
        assert ctx.agent_id == context_data["agent_id"]
        assert ctx.db_session == context_data["db_session"]
        assert ctx.llm_client == context_data["llm_client"]

    def test_context_manager(self, context_data):
        ctx = RuntimeContext(**context_data)

        # Initially no context
        assert get_runtime_context() is None

        with ctx:
            # Context set
            current = get_runtime_context()
            assert current == ctx
            assert current.agent_id == context_data["agent_id"]

            # Auth clients initialized empty
            assert _authenticated_clients.get() == {}

        # Context cleared
        assert get_runtime_context() is None
        assert _authenticated_clients.get() is None

    def test_authenticated_client_management(self, context_data):
        ctx = RuntimeContext(**context_data)
        client = MagicMock()
        client.close = MagicMock()

        with ctx:
            # Set client
            set_authenticated_client("test_service", client)

            # Get client
            retrieved = get_authenticated_client("test_service")
            assert retrieved == client

            # Clear client
            clear_authenticated_client("test_service")
            client.close.assert_called_once()
            assert get_authenticated_client("test_service") is None

    def test_context_cleanup_closes_clients(self, context_data):
        ctx = RuntimeContext(**context_data)
        client1 = MagicMock()
        client2 = MagicMock()

        with ctx:
            set_authenticated_client("service1", client1)
            set_authenticated_client("service2", client2)

        # Context exit should close clients
        client1.close.assert_called_once()
        client2.close.assert_called_once()

    def test_operations_outside_context(self):
        # Reset context vars just in case
        _runtime_context.set(None)
        _authenticated_clients.set(None)

        # Get context
        assert get_runtime_context() is None

        # Set client (should log warning but not crash)
        with patch("src.services.agents.runtime_context.logger") as mock_logger:
            set_authenticated_client("test", MagicMock())
            mock_logger.warning.assert_called_with(
                "Attempted to set authenticated client 'test' outside of runtime context"
            )

        # Get client
        with patch("src.services.agents.runtime_context.logger") as mock_logger:
            client = get_authenticated_client("test")
            assert client is None
            mock_logger.warning.assert_called_with(
                "Attempted to get authenticated client 'test' outside of runtime context"
            )
