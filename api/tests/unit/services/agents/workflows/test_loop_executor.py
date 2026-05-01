"""Unit tests for LoopExecutor."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.agents.workflows.loop_executor import LoopExecutor


@pytest.fixture
def mock_agent():
    agent = Mock()
    agent.id = uuid4()
    agent.agent_name = "loop-agent"
    agent.workflow_type = "loop"
    agent.workflow_config = {}
    return agent


@pytest.fixture
def mock_sub_agent():
    sub_agent_instance = Mock()
    sub_agent_instance.id = uuid4()
    sub_agent_instance.agent_name = "sub-agent"
    sub_agent_instance.output_key = "result"

    sub_agent = Mock()
    sub_agent.id = uuid4()
    sub_agent.sub_agent_id = sub_agent_instance.id
    sub_agent.sub_agent = sub_agent_instance
    sub_agent.execution_order = 1
    sub_agent.execution_config = {}
    return sub_agent


@pytest.mark.unit
class TestLoopExecutorBasic:
    @pytest.mark.asyncio
    async def test_executes_at_least_one_iteration(self, mock_agent, mock_sub_agent):
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        await executor.execute("start input", "user-1")

        assert executor.execute_sub_agent.call_count >= 1

    @pytest.mark.asyncio
    async def test_returns_dict_with_status(self, mock_agent, mock_sub_agent):
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        result = await executor.execute("start input", "user-1")

        assert isinstance(result, dict)
        assert "status" in result

    @pytest.mark.asyncio
    async def test_stores_total_iterations(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 3}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        await executor.execute("start input", "user-1")

        assert executor.state.get("total_iterations") == 3

    @pytest.mark.asyncio
    async def test_exit_reason_max_iterations(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 2}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        await executor.execute("start input", "user-1")

        assert executor.state.get("exit_reason") == "max_iterations"


@pytest.mark.unit
class TestLoopExecutorExitCondition:
    @pytest.mark.asyncio
    async def test_stops_when_exit_condition_met(self, mock_agent, mock_sub_agent):
        # safe_eval_condition only supports dot notation: state.done not state.get('done')
        mock_agent.workflow_config = {
            "max_iterations": 10,
            "exit_condition": "state.done == True",
        }
        executor = LoopExecutor(mock_agent, [mock_sub_agent])

        call_count = 0

        async def side_effect(sub_agent, user_id, **kwargs):
            nonlocal call_count
            call_count += 1
            # Set done=True after 2nd iteration
            if call_count >= 2:
                executor.state["done"] = True
            return "output"

        executor.execute_sub_agent = side_effect

        await executor.execute("start input", "user-1")

        assert executor.state.get("exit_reason") == "condition_met"
        assert executor.state.get("total_iterations") <= 10

    @pytest.mark.asyncio
    async def test_no_exit_condition_runs_all_iterations(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 3, "exit_condition": None}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        await executor.execute("start input", "user-1")

        assert executor.state.get("total_iterations") == 3


@pytest.mark.unit
class TestLoopExecutorErrorHandling:
    @pytest.mark.asyncio
    async def test_stops_on_error_when_stop_on_error_true(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 10, "stop_on_error": True}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])

        call_count = 0

        async def failing_after_first(sub_agent, user_id, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # Simulate failure
            return "output"

        executor.execute_sub_agent = failing_after_first

        await executor.execute("start input", "user-1")

        # Should have stopped early (stopped at sub-agent failure)
        assert executor.state.get("stopped_at") == mock_sub_agent.sub_agent.agent_name

    @pytest.mark.asyncio
    async def test_continues_when_stop_on_error_false(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 3, "stop_on_error": False}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        # Return None (failure) every time but should still run all iterations
        executor.execute_sub_agent = AsyncMock(return_value=None)

        await executor.execute("start input", "user-1")

        # All 3 iterations should have run
        assert executor.state.get("total_iterations") == 3

    @pytest.mark.asyncio
    async def test_no_sub_agents_runs_max_iterations(self, mock_agent):
        mock_agent.workflow_config = {"max_iterations": 2}
        executor = LoopExecutor(mock_agent, [])

        result = await executor.execute("start input", "user-1")

        assert executor.state.get("total_iterations") == 2
        assert "status" in result


@pytest.mark.unit
class TestLoopExecutorDefaultConfig:
    @pytest.mark.asyncio
    async def test_default_max_iterations_is_ten(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {}  # No max_iterations set
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="output")

        await executor.execute("start input", "user-1")

        assert executor.state.get("total_iterations") == 10

    @pytest.mark.asyncio
    async def test_default_stop_on_error_marks_stopped_at(self, mock_agent, mock_sub_agent):
        # stop_on_error=True (default) breaks the inner sub-agent loop when output is None,
        # recording stopped_at. The outer iteration loop is NOT broken by this alone.
        mock_agent.workflow_config = {"max_iterations": 3}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value=None)  # Always fails

        await executor.execute("start input", "user-1")

        # stopped_at should be set on the failing sub-agent
        assert executor.state.get("stopped_at") == mock_sub_agent.sub_agent.agent_name

    @pytest.mark.asyncio
    async def test_iteration_tracked_in_state(self, mock_agent, mock_sub_agent):
        mock_agent.workflow_config = {"max_iterations": 1}
        executor = LoopExecutor(mock_agent, [mock_sub_agent])
        executor.execute_sub_agent = AsyncMock(return_value="out")

        await executor.execute("start input", "user-1")

        assert executor.state.get("iteration") == 1
