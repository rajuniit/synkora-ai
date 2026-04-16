"""Tests for SequentialExecutor."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.agents.workflows.sequential_executor import SequentialExecutor


@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = Mock()
    agent.id = uuid4()
    agent.agent_name = "workflow-agent"
    agent.workflow_type = "sequential"
    agent.workflow_config = {}
    return agent


@pytest.fixture
def mock_sub_agent():
    """Create mock sub-agent."""
    sub_agent_instance = Mock()
    sub_agent_instance.id = uuid4()
    sub_agent_instance.agent_name = "sub-agent"

    sub_agent = Mock()
    sub_agent.id = uuid4()
    sub_agent.sub_agent_id = sub_agent_instance.id
    sub_agent.sub_agent = sub_agent_instance
    sub_agent.execution_order = 1
    sub_agent.execution_config = {}

    return sub_agent


@pytest.fixture
def sequential_executor(mock_agent, mock_sub_agent):
    """Create SequentialExecutor instance."""
    return SequentialExecutor(mock_agent, [mock_sub_agent])


class TestSequentialExecutor:
    """Tests for SequentialExecutor."""

    @pytest.mark.asyncio
    async def test_execute_success(self, sequential_executor, mock_agent):
        """Test successfully executing workflow."""
        # Mock execute_sub_agent to return output
        sequential_executor.execute_sub_agent = AsyncMock(return_value="Agent output")

        result = await sequential_executor.execute(
            initial_input="Test input",
            user_id="user123",
            db=Mock(),
        )

        assert result["status"] == "completed"
        assert "state" in result
        assert result["state"]["user_input"] == "Test input"

    @pytest.mark.asyncio
    async def test_execute_multiple_sub_agents(self, mock_agent):
        """Test executing multiple sub-agents in sequence."""
        # Create multiple sub-agents
        sub_agent1 = Mock()
        sub_agent1.sub_agent_id = uuid4()
        sub_agent1.sub_agent = Mock(agent_name="agent-1", id=uuid4())
        sub_agent1.execution_order = 1
        sub_agent1.execution_config = {}

        sub_agent2 = Mock()
        sub_agent2.sub_agent_id = uuid4()
        sub_agent2.sub_agent = Mock(agent_name="agent-2", id=uuid4())
        sub_agent2.execution_order = 2
        sub_agent2.execution_config = {}

        executor = SequentialExecutor(mock_agent, [sub_agent2, sub_agent1])

        # Mock execute_sub_agent
        executor.execute_sub_agent = AsyncMock(side_effect=["Output 1", "Output 2"])

        result = await executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        assert result["status"] == "completed"
        # Verify both agents were executed
        assert executor.execute_sub_agent.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_stop_on_error(self, mock_agent, mock_sub_agent):
        """Test stopping execution on error."""
        mock_agent.workflow_config = {"stop_on_error": True}

        # Create executor with stop_on_error
        executor = SequentialExecutor(mock_agent, [mock_sub_agent])

        # Mock execute_sub_agent to return None (failure)
        executor.execute_sub_agent = AsyncMock(return_value=None)

        result = await executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        assert "stopped_at" in result["state"]
        assert result["state"]["stopped_at"] == mock_sub_agent.sub_agent.agent_name

    @pytest.mark.asyncio
    async def test_execute_without_stop_on_error(self, mock_agent):
        """Test continuing execution even after error."""
        mock_agent.workflow_config = {"stop_on_error": False}

        # Create multiple sub-agents
        sub_agent1 = Mock()
        sub_agent1.sub_agent_id = uuid4()
        sub_agent1.sub_agent = Mock(agent_name="agent-1", id=uuid4())
        sub_agent1.execution_order = 1
        sub_agent1.execution_config = {}

        sub_agent2 = Mock()
        sub_agent2.sub_agent_id = uuid4()
        sub_agent2.sub_agent = Mock(agent_name="agent-2", id=uuid4())
        sub_agent2.execution_order = 2
        sub_agent2.execution_config = {}

        executor = SequentialExecutor(mock_agent, [sub_agent1, sub_agent2])

        # First agent fails, second succeeds
        executor.execute_sub_agent = AsyncMock(side_effect=[None, "Output 2"])

        result = await executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        # Both agents should be executed
        assert executor.execute_sub_agent.call_count == 2
        assert "stopped_at" not in result["state"]

    @pytest.mark.asyncio
    async def test_execute_orders_sub_agents_by_execution_order(self, mock_agent):
        """Test that sub-agents are executed in order."""
        # Create sub-agents with different orders
        sub_agent1 = Mock()
        sub_agent1.sub_agent_id = uuid4()
        sub_agent1.sub_agent = Mock(agent_name="agent-1", id=uuid4())
        sub_agent1.execution_order = 3
        sub_agent1.execution_config = {}

        sub_agent2 = Mock()
        sub_agent2.sub_agent_id = uuid4()
        sub_agent2.sub_agent = Mock(agent_name="agent-2", id=uuid4())
        sub_agent2.execution_order = 1
        sub_agent2.execution_config = {}

        sub_agent3 = Mock()
        sub_agent3.sub_agent_id = uuid4()
        sub_agent3.sub_agent = Mock(agent_name="agent-3", id=uuid4())
        sub_agent3.execution_order = 2
        sub_agent3.execution_config = {}

        # Pass in wrong order
        executor = SequentialExecutor(mock_agent, [sub_agent1, sub_agent3, sub_agent2])

        # Track execution order
        execution_order = []

        async def track_execution(sub_agent, *args, **kwargs):
            execution_order.append(sub_agent.sub_agent.agent_name)
            return "output"

        executor.execute_sub_agent = track_execution

        await executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        # Verify correct execution order
        assert execution_order == ["agent-2", "agent-3", "agent-1"]

    @pytest.mark.asyncio
    async def test_execute_with_empty_sub_agents(self, mock_agent):
        """Test executing workflow with no sub-agents."""
        executor = SequentialExecutor(mock_agent, [])

        result = await executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        assert result["status"] == "completed"
        assert result["state"]["user_input"] == "Test"

    @pytest.mark.asyncio
    async def test_execute_initializes_state(self, sequential_executor):
        """Test that execution initializes state correctly."""
        sequential_executor.execute_sub_agent = AsyncMock(return_value="output")

        await sequential_executor.execute(
            initial_input="Test input",
            user_id="user123",
            db=Mock(),
        )

        assert "user_input" in sequential_executor.state
        assert "workflow_start_time" in sequential_executor.state
        assert sequential_executor.state["user_input"] == "Test input"

    @pytest.mark.asyncio
    async def test_execute_returns_final_result(self, sequential_executor):
        """Test that execution returns final result."""
        sequential_executor.execute_sub_agent = AsyncMock(return_value="output")

        result = await sequential_executor.execute(
            initial_input="Test",
            user_id="user123",
            db=Mock(),
        )

        assert "state" in result
        assert "execution_log" in result
        assert "status" in result
        assert "workflow_type" in result
