"""Unit tests for WorkflowFactory."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.services.agents.workflows.custom_executor import CustomExecutor
from src.services.agents.workflows.loop_executor import LoopExecutor
from src.services.agents.workflows.parallel_executor import ParallelExecutor
from src.services.agents.workflows.sequential_executor import SequentialExecutor
from src.services.agents.workflows.workflow_factory import WorkflowFactory


def _agent(workflow_type=None):
    agent = Mock()
    agent.id = uuid4()
    agent.agent_name = "test-agent"
    agent.workflow_type = workflow_type
    agent.workflow_config = {}
    return agent


def _sub_agent():
    sa = Mock()
    sa.id = uuid4()
    sa.execution_order = 1
    sa.sub_agent = Mock()
    sa.sub_agent.id = uuid4()
    sa.sub_agent.agent_name = "sub"
    return sa


@pytest.mark.unit
class TestCreateExecutor:
    def test_no_workflow_type_returns_none(self):
        assert WorkflowFactory.create_executor(_agent(None), [_sub_agent()]) is None

    def test_empty_string_workflow_type_returns_none(self):
        assert WorkflowFactory.create_executor(_agent(""), [_sub_agent()]) is None

    def test_no_sub_agents_returns_none(self):
        assert WorkflowFactory.create_executor(_agent("sequential"), []) is None

    def test_sequential_creates_sequential_executor(self):
        result = WorkflowFactory.create_executor(_agent("sequential"), [_sub_agent()])
        assert isinstance(result, SequentialExecutor)

    def test_loop_creates_loop_executor(self):
        result = WorkflowFactory.create_executor(_agent("loop"), [_sub_agent()])
        assert isinstance(result, LoopExecutor)

    def test_parallel_creates_parallel_executor(self):
        result = WorkflowFactory.create_executor(_agent("parallel"), [_sub_agent()])
        assert isinstance(result, ParallelExecutor)

    def test_custom_creates_custom_executor(self):
        result = WorkflowFactory.create_executor(_agent("custom"), [_sub_agent()])
        assert isinstance(result, CustomExecutor)

    def test_unknown_type_returns_none(self):
        result = WorkflowFactory.create_executor(_agent("unknown_xyz"), [_sub_agent()])
        assert result is None

    def test_executor_receives_correct_agent(self):
        agent = _agent("sequential")
        result = WorkflowFactory.create_executor(agent, [_sub_agent()])
        assert result.agent is agent

    def test_executor_receives_sub_agents(self):
        subs = [_sub_agent(), _sub_agent()]
        result = WorkflowFactory.create_executor(_agent("sequential"), subs)
        assert len(result.sub_agents) == 2


@pytest.mark.unit
class TestGetSupportedWorkflowTypes:
    def test_returns_list(self):
        result = WorkflowFactory.get_supported_workflow_types()
        assert isinstance(result, list)

    def test_contains_all_four_types(self):
        result = WorkflowFactory.get_supported_workflow_types()
        assert "sequential" in result
        assert "loop" in result
        assert "parallel" in result
        assert "custom" in result

    def test_returns_four_types(self):
        assert len(WorkflowFactory.get_supported_workflow_types()) == 4


@pytest.mark.unit
class TestGetWorkflowTypeInfo:
    def test_sequential_info_has_required_fields(self):
        info = WorkflowFactory.get_workflow_type_info("sequential")
        assert "name" in info
        assert "description" in info
        assert "config_schema" in info
        assert "use_cases" in info

    def test_loop_info_has_max_iterations_schema(self):
        info = WorkflowFactory.get_workflow_type_info("loop")
        assert "max_iterations" in info["config_schema"]

    def test_parallel_info_has_wait_for_all_schema(self):
        info = WorkflowFactory.get_workflow_type_info("parallel")
        assert "wait_for_all" in info["config_schema"]

    def test_custom_info_has_nodes_schema(self):
        info = WorkflowFactory.get_workflow_type_info("custom")
        assert "nodes" in info["config_schema"]

    def test_unknown_type_returns_empty_dict(self):
        info = WorkflowFactory.get_workflow_type_info("nonexistent")
        assert info == {}

    def test_all_supported_types_have_info(self):
        for wtype in WorkflowFactory.get_supported_workflow_types():
            info = WorkflowFactory.get_workflow_type_info(wtype)
            assert info != {}, f"Missing info for workflow type: {wtype}"

    def test_use_cases_is_list(self):
        for wtype in WorkflowFactory.get_supported_workflow_types():
            info = WorkflowFactory.get_workflow_type_info(wtype)
            assert isinstance(info["use_cases"], list)
