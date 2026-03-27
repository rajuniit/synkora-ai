"""Unit tests for agent configuration Pydantic models."""

import pytest
from pydantic import ValidationError

from src.services.agents.config import (
    AgentConfig,
    AgenticConfig,
    AgentStatus,
    AgentType,
    DeploymentConfig,
    ModelConfig,
    ToolConfig,
    WorkflowConfig,
)


@pytest.mark.unit
class TestAgentType:
    def test_sequential_value(self):
        assert AgentType.SEQUENTIAL == "sequential"

    def test_all_types_are_strings(self):
        for member in AgentType:
            assert isinstance(member.value, str)

    def test_llm_agent_default(self):
        assert AgentType.LLM_AGENT == "llm_agent"


@pytest.mark.unit
class TestAgentStatus:
    def test_idle_value(self):
        assert AgentStatus.IDLE == "idle"

    def test_running_value(self):
        assert AgentStatus.RUNNING == "running"

    def test_all_statuses_are_strings(self):
        for member in AgentStatus:
            assert isinstance(member.value, str)


@pytest.mark.unit
class TestAgenticConfig:
    def test_defaults(self):
        cfg = AgenticConfig()
        assert cfg.max_iterations == 150
        assert cfg.tool_choice == "auto"
        assert cfg.parallel_tools is True
        assert cfg.tool_retry_attempts == 2
        assert cfg.tool_retry_delay == 1.0
        assert cfg.thinking_enabled is False

    def test_override_values(self):
        cfg = AgenticConfig(max_iterations=50, tool_choice="required", thinking_enabled=True)
        assert cfg.max_iterations == 50
        assert cfg.tool_choice == "required"
        assert cfg.thinking_enabled is True


@pytest.mark.unit
class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.provider == "gemini"
        assert "gemini" in cfg.model_name
        assert cfg.temperature == 0.7
        assert cfg.max_tokens is None
        assert cfg.api_key is None
        assert cfg.additional_params == {}

    def test_temperature_accepts_zero(self):
        cfg = ModelConfig(temperature=0.0)
        assert cfg.temperature == 0.0

    def test_temperature_accepts_two(self):
        cfg = ModelConfig(temperature=2.0)
        assert cfg.temperature == 2.0

    def test_temperature_rejects_below_zero(self):
        with pytest.raises(ValidationError):
            ModelConfig(temperature=-0.1)

    def test_temperature_rejects_above_two(self):
        with pytest.raises(ValidationError):
            ModelConfig(temperature=2.1)

    def test_top_p_range(self):
        ModelConfig(top_p=0.0)
        ModelConfig(top_p=1.0)
        with pytest.raises(ValidationError):
            ModelConfig(top_p=-0.1)
        with pytest.raises(ValidationError):
            ModelConfig(top_p=1.1)

    def test_custom_provider(self):
        cfg = ModelConfig(provider="openai", model_name="gpt-4", api_key="sk-test")
        assert cfg.provider == "openai"
        assert cfg.api_key == "sk-test"

    def test_additional_params_stored(self):
        cfg = ModelConfig(additional_params={"stream": True})
        assert cfg.additional_params["stream"] is True


@pytest.mark.unit
class TestToolConfig:
    def test_minimal_required_fields(self):
        cfg = ToolConfig(name="search", description="Search the web")
        assert cfg.name == "search"
        assert cfg.description == "Search the web"
        assert cfg.enabled is True
        assert cfg.parameters == {}

    def test_disabled_tool(self):
        cfg = ToolConfig(name="t", description="d", enabled=False)
        assert cfg.enabled is False

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            ToolConfig(description="desc")

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError):
            ToolConfig(name="t")

    def test_parameters_stored(self):
        params = {"query": {"type": "string"}}
        cfg = ToolConfig(name="t", description="d", parameters=params)
        assert cfg.parameters == params


@pytest.mark.unit
class TestAgentConfig:
    def test_minimal_required_fields(self):
        cfg = AgentConfig(name="my-agent", description="Does things")
        assert cfg.name == "my-agent"
        assert cfg.description == "Does things"

    def test_defaults(self):
        cfg = AgentConfig(name="a", description="b")
        assert cfg.agent_type == AgentType.LLM_AGENT
        assert cfg.max_iterations == 150
        assert cfg.timeout == 300
        assert cfg.memory_enabled is True
        assert cfg.tools == []
        assert cfg.suggestion_prompts == []
        assert cfg.metadata == {}
        assert cfg.avatar is None
        assert cfg.system_prompt is None

    def test_llm_config_defaults(self):
        cfg = AgentConfig(name="a", description="b")
        assert isinstance(cfg.llm_config, ModelConfig)

    def test_max_iterations_ge_one(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="a", description="b", max_iterations=0)

    def test_timeout_ge_one(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="a", description="b", timeout=0)

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            AgentConfig(description="b")

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="a")

    def test_agent_type_enum_coercion(self):
        cfg = AgentConfig(name="a", description="b", agent_type="parallel")
        assert cfg.agent_type == "parallel"

    def test_tools_stored(self):
        tool = ToolConfig(name="t", description="d")
        cfg = AgentConfig(name="a", description="b", tools=[tool])
        assert len(cfg.tools) == 1
        assert cfg.tools[0].name == "t"


@pytest.mark.unit
class TestWorkflowConfig:
    def test_minimal_required_fields(self):
        cfg = WorkflowConfig(name="wf", description="my workflow", agents=["a", "b"])
        assert cfg.name == "wf"
        assert cfg.agents == ["a", "b"]

    def test_defaults(self):
        cfg = WorkflowConfig(name="wf", description="d", agents=["a"])
        assert cfg.execution_mode == "sequential"
        assert cfg.max_retries == 3
        assert cfg.routing_logic is None
        assert cfg.metadata == {}

    def test_max_retries_ge_zero(self):
        with pytest.raises(ValidationError):
            WorkflowConfig(name="wf", description="d", agents=["a"], max_retries=-1)

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            WorkflowConfig(description="d", agents=["a"])


@pytest.mark.unit
class TestDeploymentConfig:
    def test_defaults(self):
        cfg = DeploymentConfig()
        assert cfg.environment == "development"
        assert cfg.scaling["min_instances"] == 1
        assert cfg.scaling["max_instances"] == 10
        assert cfg.monitoring["enabled"] is True
        assert cfg.logging["level"] == "INFO"

    def test_override_environment(self):
        cfg = DeploymentConfig(environment="production")
        assert cfg.environment == "production"

    def test_custom_scaling(self):
        cfg = DeploymentConfig(scaling={"min_instances": 2, "max_instances": 20})
        assert cfg.scaling["min_instances"] == 2
