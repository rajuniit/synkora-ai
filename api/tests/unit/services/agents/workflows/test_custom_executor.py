"""Unit tests for CustomExecutor."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.agents.workflows.custom_executor import CustomExecutor


def _make_agent(nodes=None, stop_on_error=True):
    agent = Mock()
    agent.id = uuid4()
    agent.agent_name = "custom-agent"
    agent.workflow_type = "custom"
    config = {}
    if nodes is not None:
        config["nodes"] = nodes
    config["stop_on_error"] = stop_on_error
    agent.workflow_config = config
    return agent


def _make_sub(name: str, role: str | None = None):
    sub_inst = Mock()
    sub_inst.id = uuid4()
    sub_inst.agent_name = name
    sub_inst.output_key = name

    sub = Mock()
    sub.id = uuid4()
    sub.sub_agent_id = sub_inst.id
    sub.sub_agent = sub_inst
    sub.execution_order = 1
    sub.execution_config = {"role": role} if role else {}
    return sub


@pytest.mark.unit
class TestCustomExecutorNoNodes:
    @pytest.mark.asyncio
    async def test_returns_error_state_when_no_nodes(self):
        agent = _make_agent(nodes=None)
        agent.workflow_config = {}  # No nodes key at all
        executor = CustomExecutor(agent, [_make_sub("a")])
        executor.execute_sub_agent = AsyncMock(return_value="out")
        await executor.execute("input", "user-1")
        assert "error" in executor.state

    @pytest.mark.asyncio
    async def test_returns_error_state_when_nodes_empty(self):
        executor = CustomExecutor(_make_agent(nodes=[]), [_make_sub("a")])
        executor.execute_sub_agent = AsyncMock(return_value="out")
        await executor.execute("input", "user-1")
        assert "error" in executor.state


@pytest.mark.unit
class TestCustomExecutorSequentialStage:
    @pytest.mark.asyncio
    async def test_sequential_stage_runs_agents_in_order(self):
        sub_a = _make_sub("agent-a")
        sub_b = _make_sub("agent-b")
        nodes = [{"type": "sequential", "agents": ["agent-a", "agent-b"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub_a, sub_b])

        call_order = []

        async def track(sub_agent, user_id, **kwargs):
            call_order.append(sub_agent.sub_agent.agent_name)
            return f"out-{sub_agent.sub_agent.agent_name}"

        executor.execute_sub_agent = track
        await executor.execute("input", "user-1")
        assert call_order == ["agent-a", "agent-b"]

    @pytest.mark.asyncio
    async def test_agent_stage_type_also_runs_sequentially(self):
        sub_a = _make_sub("writer")
        nodes = [{"type": "agent", "agents": ["writer"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub_a])
        executor.execute_sub_agent = AsyncMock(return_value="output")
        await executor.execute("input", "user-1")
        executor.execute_sub_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_previous_output_stored_in_state(self):
        sub_a = _make_sub("a")
        sub_b = _make_sub("b")
        nodes = [{"type": "sequential", "agents": ["a", "b"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub_a, sub_b])

        call_count = 0

        async def side_effect(sub_agent, user_id, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"result-{call_count}"

        executor.execute_sub_agent = side_effect
        await executor.execute("input", "user-1")
        assert executor.state.get("previous_output") == "result-1"

    @pytest.mark.asyncio
    async def test_stops_on_none_output_when_stop_on_error_true(self):
        sub_a = _make_sub("a")
        sub_b = _make_sub("b")
        nodes = [{"type": "sequential", "agents": ["a", "b"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes, stop_on_error=True), [sub_a, sub_b])

        call_count = 0

        async def failing(sub_agent, user_id, **kwargs):
            nonlocal call_count
            call_count += 1
            return None  # Always fail

        executor.execute_sub_agent = failing
        await executor.execute("input", "user-1")
        # Should stop after first agent
        assert call_count == 1
        assert executor.state.get("stopped_at") == "a"


@pytest.mark.unit
class TestCustomExecutorLoopStage:
    @pytest.mark.asyncio
    async def test_loop_stage_runs_n_iterations(self):
        sub = _make_sub("refiner")
        nodes = [{"type": "loop", "agents": ["refiner"], "iterations": 3}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="refined")
        await executor.execute("input", "user-1")
        assert executor.execute_sub_agent.call_count == 3

    @pytest.mark.asyncio
    async def test_loop_stage_default_iteration_is_one(self):
        sub = _make_sub("refiner")
        nodes = [{"type": "loop", "agents": ["refiner"]}]  # No iterations key
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="done")
        await executor.execute("input", "user-1")
        assert executor.execute_sub_agent.call_count == 1

    @pytest.mark.asyncio
    async def test_loop_iteration_tracked_in_state(self):
        sub = _make_sub("refiner")
        nodes = [{"type": "loop", "agents": ["refiner"], "iterations": 2}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="out")
        await executor.execute("input", "user-1")
        assert executor.state.get("iteration") == 2


@pytest.mark.unit
class TestCustomExecutorParallelStage:
    @pytest.mark.asyncio
    async def test_parallel_stage_runs_all_agents(self):
        sub_a = _make_sub("a")
        sub_b = _make_sub("b")
        nodes = [{"type": "parallel", "agents": ["a", "b"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub_a, sub_b])
        executor.execute_sub_agent = AsyncMock(return_value="out")
        await executor.execute("input", "user-1")
        assert executor.execute_sub_agent.call_count == 2

    @pytest.mark.asyncio
    async def test_parallel_exception_sets_error_state(self):
        sub_a = _make_sub("a")
        nodes = [{"type": "parallel", "agents": ["a"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes, stop_on_error=True), [sub_a])
        executor.execute_sub_agent = AsyncMock(side_effect=RuntimeError("boom"))
        await executor.execute("input", "user-1")
        assert "error" in executor.state or executor.state.get("stopped_at") is not None


@pytest.mark.unit
class TestCustomExecutorUnknownStage:
    @pytest.mark.asyncio
    async def test_unknown_stage_type_sets_error(self):
        sub = _make_sub("a")
        nodes = [{"type": "banana", "agents": ["a"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes, stop_on_error=True), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="out")
        await executor.execute("input", "user-1")
        assert "error" in executor.state


@pytest.mark.unit
class TestCustomExecutorResolveSubAgents:
    def setup_method(self):
        self.sub_a = _make_sub("agent-a")
        self.sub_b = _make_sub("agent-b", role="editor")
        self.executor = CustomExecutor(_make_agent(nodes=[]), [self.sub_a, self.sub_b])

    def test_no_stage_returns_all_sub_agents(self):
        result = self.executor._resolve_sub_agents(None)
        assert len(result) == 2

    def test_resolve_by_agent_name(self):
        result = self.executor._resolve_sub_agents({"agents": ["agent-a"]})
        assert len(result) == 1
        assert result[0] is self.sub_a

    def test_resolve_by_role(self):
        result = self.executor._resolve_sub_agents({"roles": ["editor"]})
        assert len(result) == 1
        assert result[0] is self.sub_b

    def test_resolve_by_index(self):
        result = self.executor._resolve_sub_agents({"indices": [0]})
        assert len(result) == 1
        assert result[0] is self.sub_a

    def test_out_of_bounds_index_ignored(self):
        result = self.executor._resolve_sub_agents({"indices": [99]})
        assert result == []

    def test_empty_agents_list_returns_all(self):
        result = self.executor._resolve_sub_agents({"agents": []})
        assert result == self.executor.sub_agents

    def test_unknown_agent_name_skipped(self):
        result = self.executor._resolve_sub_agents({"agents": ["does-not-exist"]})
        assert result == []


@pytest.mark.unit
class TestCustomExecutorFinalOutput:
    @pytest.mark.asyncio
    async def test_final_response_stored_in_state(self):
        sub = _make_sub("writer")
        nodes = [{"type": "agent", "agents": ["writer"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="final output text")
        await executor.execute("input", "user-1")
        assert executor.state.get("final_response") == "final output text"

    @pytest.mark.asyncio
    async def test_result_has_status_key(self):
        sub = _make_sub("a")
        nodes = [{"type": "sequential", "agents": ["a"]}]
        executor = CustomExecutor(_make_agent(nodes=nodes), [sub])
        executor.execute_sub_agent = AsyncMock(return_value="done")
        result = await executor.execute("input", "user-1")
        assert "status" in result
