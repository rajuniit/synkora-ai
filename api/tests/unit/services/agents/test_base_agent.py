from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig, AgentStatus, ModelConfig


# Concrete implementation for testing abstract base class
class ConcreteAgent(BaseAgent):
    async def execute(self, input_data):
        return {"output": "processed"}


class TestBaseAgent:
    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            name="TestAgent",
            description="Test",
            llm_config=ModelConfig(provider="openai", model_name="gpt-4", api_key="test-key"),
        )

    @pytest.fixture
    def agent(self, agent_config):
        return ConcreteAgent(agent_config)

    def test_init(self, agent, agent_config):
        assert agent.config == agent_config
        assert agent.status == AgentStatus.IDLE
        assert agent.execution_count == 0
        assert agent.error_count == 0
        assert agent.agent_id is not None

    def test_initialize_client(self, agent):
        with patch("src.services.agents.base_agent.get_llm_client_pool") as mock_get_pool:
            mock_pool = MagicMock()
            mock_client = MagicMock()
            mock_pool.get_client.return_value = mock_client
            mock_get_pool.return_value = mock_pool

            agent.initialize_client()

            mock_get_pool.assert_called_once()
            mock_pool.get_client.assert_called_once()
            assert agent.llm_client == mock_client

    def test_initialize_client_no_key(self, agent):
        agent.config.llm_config.api_key = None
        with pytest.raises(ValueError, match="API key is required"):
            agent.initialize_client()

    @pytest.mark.asyncio
    async def test_run_success(self, agent):
        input_data = {"input": "test"}

        # Mock tracing
        agent.langfuse_service = MagicMock()
        agent.langfuse_service.should_trace.return_value = True
        agent.langfuse_service.create_trace.return_value = "trace-id"

        result = await agent.run(input_data)

        assert result["status"] == "success"
        assert result["result"] == {"output": "processed"}
        assert agent.status == AgentStatus.COMPLETED
        assert agent.execution_count == 1

        # Verify history
        assert len(agent._history) == 1
        assert agent._history[0]["status"] == "success"

        # Verify trace update
        agent.langfuse_service.update_trace.assert_called()

    @pytest.mark.asyncio
    async def test_run_failure(self, agent):
        # Make execute fail
        agent.execute = AsyncMock(side_effect=Exception("Execution failed"))

        result = await agent.run({"input": "test"})

        assert result["status"] == "error"
        assert "Execution failed" in result["error"]
        assert agent.status == AgentStatus.FAILED
        assert agent.error_count == 1

        # Verify history
        assert len(agent._history) == 1
        assert agent._history[0]["status"] == "error"

    def test_history_management(self, agent):
        agent._add_to_history({}, {}, "success", 1.0)
        assert len(agent.get_history()) == 1

        agent.clear_history()
        assert len(agent.get_history()) == 0

    def test_get_stats(self, agent):
        stats = agent.get_stats()
        assert stats["agent_name"] == "TestAgent"
        assert stats["execution_count"] == 0
        assert stats["success_rate"] == 0

    def test_reset(self, agent):
        agent.execution_count = 5
        agent.error_count = 1
        agent.status = AgentStatus.COMPLETED
        agent._add_to_history({}, {}, "success", 1.0)

        agent.reset()

        assert agent.execution_count == 0
        assert agent.error_count == 0
        assert agent.status == AgentStatus.IDLE
        assert len(agent.get_history()) == 0
