"""Tests for BaseWorkflowExecutor."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Note: conftest.py in this directory sets up the security module mock
from src.services.agents.workflows.base_executor import BaseWorkflowExecutor


# Create a concrete implementation for testing
class TestExecutor(BaseWorkflowExecutor):
    """Test implementation of BaseWorkflowExecutor."""

    async def execute(self, initial_input: str, user_id: str, **kwargs):
        self.initialize_state(initial_input)
        return self.get_final_result()


@pytest.fixture
def mock_agent():
    """Create mock agent."""
    agent = Mock()
    agent.id = uuid4()
    agent.agent_name = "test-agent"
    agent.workflow_type = "test"
    agent.workflow_config = {}
    return agent


@pytest.fixture
def mock_sub_agent():
    """Create mock sub-agent."""
    sub_agent_id = uuid4()

    sub_agent_instance = Mock()
    sub_agent_instance.id = sub_agent_id
    sub_agent_instance.agent_name = "sub-agent"
    sub_agent_instance.output_key = None

    sub_agent = Mock()
    sub_agent.id = uuid4()
    sub_agent.sub_agent_id = sub_agent_id
    sub_agent.sub_agent = sub_agent_instance
    sub_agent.execution_order = 1
    sub_agent.execution_config = {}

    return sub_agent


@pytest.fixture
def executor(mock_agent, mock_sub_agent):
    """Create test executor instance."""
    return TestExecutor(mock_agent, [mock_sub_agent])


class TestInitialization:
    """Tests for initialization."""

    def test_init(self, mock_agent, mock_sub_agent):
        """Test executor initialization."""
        executor = TestExecutor(mock_agent, [mock_sub_agent])

        assert executor.agent == mock_agent
        assert len(executor.sub_agents) == 1
        assert executor.state == {}
        assert executor.execution_log == []

    def test_init_sorts_sub_agents_by_execution_order(self, mock_agent):
        """Test that sub-agents are sorted by execution_order."""
        sub_agent1 = Mock(execution_order=3)
        sub_agent2 = Mock(execution_order=1)
        sub_agent3 = Mock(execution_order=2)

        executor = TestExecutor(mock_agent, [sub_agent1, sub_agent2, sub_agent3])

        assert executor.sub_agents[0].execution_order == 1
        assert executor.sub_agents[1].execution_order == 2
        assert executor.sub_agents[2].execution_order == 3


class TestStateManagement:
    """Tests for state management methods."""

    def test_initialize_state(self, executor):
        """Test state initialization."""
        executor.initialize_state("test input")

        assert executor.state["user_input"] == "test input"
        assert "workflow_start_time" in executor.state
        assert executor.state["iteration"] == 0

    def test_get_state_value(self, executor):
        """Test getting state value."""
        executor.state = {"key1": "value1", "key2": 123}

        assert executor.get_state_value("key1") == "value1"
        assert executor.get_state_value("key2") == 123
        assert executor.get_state_value("nonexistent") is None
        assert executor.get_state_value("nonexistent", "default") == "default"

    def test_set_state_value(self, executor):
        """Test setting state value."""
        executor.set_state_value("test_key", "test_value")

        assert executor.state["test_key"] == "test_value"

    def test_set_state_value_overwrites(self, executor):
        """Test that setting value overwrites existing."""
        executor.state["key"] = "old"
        executor.set_state_value("key", "new")

        assert executor.state["key"] == "new"


class TestConditionEvaluation:
    """Tests for condition evaluation."""

    def test_evaluate_condition_none(self, executor):
        """Test evaluating None condition returns True."""
        assert executor.evaluate_condition(None) is True

    def test_evaluate_condition_empty_string(self, executor):
        """Test evaluating empty string returns True."""
        assert executor.evaluate_condition("") is True

    def test_evaluate_condition_simple_comparison(self, executor):
        """Test simple state comparison."""
        executor.state = {"value": 10}

        assert executor.evaluate_condition("state['value'] > 5") is True
        assert executor.evaluate_condition("state['value'] < 5") is False

    def test_evaluate_condition_with_string_comparison(self, executor):
        """Test condition with string comparison."""
        executor.state = {"text": "hello"}

        assert executor.evaluate_condition("state['text'] == 'hello'") is True
        assert executor.evaluate_condition("state['text'] != 'world'") is True

    def test_evaluate_condition_invalid_syntax(self, executor):
        """Test that invalid syntax returns False."""
        result = executor.evaluate_condition("invalid syntax {{")
        assert result is False

    def test_evaluate_condition_missing_key(self, executor):
        """Test condition with missing state key."""
        result = executor.evaluate_condition("state['nonexistent'] == 1")
        assert result is False

    def test_evaluate_condition_multiple_conditions(self, executor):
        """Test complex conditions with boolean operators."""
        executor.state = {"a": 10, "b": 20}

        assert executor.evaluate_condition("state['a'] < state['b']") is True
        assert executor.evaluate_condition("state['a'] < state['b'] and state['a'] > 0") is True
        assert executor.evaluate_condition("state['a'] > 100 or state['b'] == 20") is True


class TestAgentInputRetrieval:
    """Tests for get_agent_input method."""

    def test_get_agent_input_with_user_input_only(self, executor, mock_sub_agent):
        """Test getting input with only user input."""
        executor.state = {"user_input": "Hello"}

        result = executor.get_agent_input(mock_sub_agent)

        assert result == "Hello"

    def test_get_agent_input_with_previous_output(self, executor, mock_sub_agent):
        """Test getting input with previous agent output."""
        executor.state = {"user_input": "Hello", "previous_output": "Previous response"}

        result = executor.get_agent_input(mock_sub_agent)

        assert "Hello" in result
        assert "Previous response" in result
        assert "[Previous Agent Output]" in result

    def test_get_agent_input_with_input_keys(self, executor, mock_sub_agent):
        """Test getting input using input_keys."""
        mock_sub_agent.execution_config = {"input_keys": ["data1", "data2"]}
        executor.state = {
            "user_input": "Hello",
            "data1": "Value 1",
            "data2": "Value 2",
        }

        result = executor.get_agent_input(mock_sub_agent)

        assert "data1: Value 1" in result
        assert "data2: Value 2" in result

    def test_get_agent_input_with_missing_input_keys(self, executor, mock_sub_agent):
        """Test getting input when input_keys don't exist."""
        mock_sub_agent.execution_config = {"input_keys": ["nonexistent"]}
        executor.state = {"user_input": "Hello"}

        result = executor.get_agent_input(mock_sub_agent)

        assert result == "Hello"


class TestOutputStorage:
    """Tests for store_agent_output method."""

    def test_store_agent_output_default_key(self, executor, mock_sub_agent):
        """Test storing output with default key."""
        # Ensure sub_agent.output_key is None so it falls through to default
        mock_sub_agent.sub_agent.output_key = None
        mock_sub_agent.execution_config = {}

        executor.store_agent_output(mock_sub_agent, "Test output")

        expected_key = f"agent_{mock_sub_agent.sub_agent_id}_output"
        assert executor.state[expected_key] == "Test output"

    def test_store_agent_output_custom_key(self, executor, mock_sub_agent):
        """Test storing output with custom key."""
        mock_sub_agent.execution_config = {"output_key": "custom_output"}

        executor.store_agent_output(mock_sub_agent, "Test output")

        assert executor.state["custom_output"] == "Test output"

    def test_store_agent_output_from_agent_attribute(self, executor, mock_sub_agent):
        """Test storing output using sub_agent.output_key."""
        mock_sub_agent.sub_agent.output_key = "agent_output_key"

        executor.store_agent_output(mock_sub_agent, "Test output")

        assert executor.state["agent_output_key"] == "Test output"


class TestExecutionLogging:
    """Tests for log_execution method."""

    def test_log_execution(self, executor):
        """Test logging execution event."""
        executor.log_execution(sub_agent_id="agent-123", status="started", input="test input")

        assert len(executor.execution_log) == 1
        log = executor.execution_log[0]
        assert log["sub_agent_id"] == "agent-123"
        assert log["status"] == "started"
        assert log["input"] == "test input"
        assert "timestamp" in log

    def test_log_execution_multiple_events(self, executor):
        """Test logging multiple events."""
        executor.log_execution("agent-1", "started")
        executor.log_execution("agent-1", "completed")
        executor.log_execution("agent-2", "started")

        assert len(executor.execution_log) == 3


class TestExecuteSubAgent:
    """Tests for execute_sub_agent method."""

    @pytest.mark.asyncio
    async def test_execute_sub_agent_success(self, executor, mock_sub_agent):
        """Test successful sub-agent execution."""
        mock_db = AsyncMock(spec=AsyncSession)
        executor.state = {"user_input": "test"}  # Initialize state

        with patch("src.services.agents.agent_tool.execute_agent") as mock_execute:
            mock_execute.return_value = {"response": "Agent response"}

            result = await executor.execute_sub_agent(mock_sub_agent, user_id="user123", db=mock_db)

        assert result == "Agent response"
        assert len(executor.execution_log) == 2  # started and completed

    @pytest.mark.asyncio
    async def test_execute_sub_agent_with_condition_met(self, executor, mock_sub_agent):
        """Test executing sub-agent when condition is met."""
        mock_sub_agent.execution_config = {"condition": "state['value'] > 5"}
        executor.state = {"value": 10, "user_input": "test"}
        mock_db = AsyncMock(spec=AsyncSession)

        with patch("src.services.agents.agent_tool.execute_agent") as mock_execute:
            mock_execute.return_value = {"response": "Response"}

            result = await executor.execute_sub_agent(mock_sub_agent, user_id="user123", db=mock_db)

        assert result == "Response"

    @pytest.mark.asyncio
    async def test_execute_sub_agent_with_condition_not_met(self, executor, mock_sub_agent):
        """Test skipping sub-agent when condition is not met."""
        mock_sub_agent.execution_config = {"condition": "state['value'] > 5"}
        executor.state = {"value": 2}

        result = await executor.execute_sub_agent(mock_sub_agent, user_id="user123", db=AsyncMock(spec=AsyncSession))

        assert result is None
        # Check log for skipped event
        assert any(log["status"] == "skipped" for log in executor.execution_log)

    @pytest.mark.asyncio
    async def test_execute_sub_agent_without_db(self, executor, mock_sub_agent):
        """Test error when db is not provided."""
        result = await executor.execute_sub_agent(mock_sub_agent, user_id="user123")

        assert result is None
        assert "error" in executor.state
        assert any(log["status"] == "failed" for log in executor.execution_log)

    @pytest.mark.asyncio
    async def test_execute_sub_agent_with_error(self, executor, mock_sub_agent):
        """Test handling error during sub-agent execution."""
        mock_db = AsyncMock(spec=AsyncSession)
        executor.state = {"user_input": "test"}  # Initialize state

        with patch("src.services.agents.agent_tool.execute_agent") as mock_execute:
            mock_execute.side_effect = Exception("Execution error")

            result = await executor.execute_sub_agent(mock_sub_agent, user_id="user123", db=mock_db)

        assert result is None
        assert "error" in executor.state
        assert executor.state["error"] == "Execution error"
        assert any(log["status"] == "failed" for log in executor.execution_log)

    @pytest.mark.asyncio
    async def test_execute_sub_agent_with_event_callback(self, executor, mock_sub_agent):
        """Test sub-agent execution with event callback."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_callback = AsyncMock()
        executor.state = {"user_input": "test"}  # Initialize state

        with patch("src.services.agents.agent_tool.execute_agent") as mock_execute:
            mock_execute.return_value = {"response": "Response"}

            await executor.execute_sub_agent(
                mock_sub_agent, user_id="user123", db=mock_db, event_callback=mock_callback
            )

        # Verify callbacks were called for start and done events
        assert mock_callback.call_count >= 2
        calls = [call[0][0] for call in mock_callback.call_args_list]
        assert "start" in calls
        assert "done" in calls

    @pytest.mark.asyncio
    async def test_execute_sub_agent_stores_output(self, executor, mock_sub_agent):
        """Test that sub-agent output is stored in state."""
        mock_db = AsyncMock(spec=AsyncSession)
        executor.state = {"user_input": "test"}  # Initialize state
        mock_sub_agent.sub_agent.output_key = None
        mock_sub_agent.execution_config = {}

        with patch("src.services.agents.agent_tool.execute_agent") as mock_execute:
            mock_execute.return_value = {"response": "Test output"}

            await executor.execute_sub_agent(mock_sub_agent, user_id="user123", db=mock_db)

        # Verify output was stored
        expected_key = f"agent_{mock_sub_agent.sub_agent_id}_output"
        assert executor.state[expected_key] == "Test output"


class TestGetFinalResult:
    """Tests for get_final_result method."""

    def test_get_final_result_success(self, executor, mock_agent):
        """Test getting final result on success."""
        executor.state = {"user_input": "test", "result": "success"}
        executor.log_execution("agent-1", "completed")

        result = executor.get_final_result()

        assert result["status"] == "completed"
        assert result["state"] == executor.state
        assert len(result["execution_log"]) == 1
        assert result["workflow_type"] == mock_agent.workflow_type

    def test_get_final_result_with_error(self, executor, mock_agent):
        """Test getting final result when error occurred."""
        executor.state = {"error": "Something went wrong"}
        executor.log_execution("agent-1", "failed", error="Something went wrong")

        result = executor.get_final_result()

        assert result["status"] == "failed"
        assert result["state"]["error"] == "Something went wrong"

    def test_get_final_result_empty_state(self, executor, mock_agent):
        """Test getting final result with empty state."""
        result = executor.get_final_result()

        assert result["status"] == "completed"
        assert result["state"] == {}
        assert result["execution_log"] == []
