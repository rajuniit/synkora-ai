from unittest.mock import MagicMock, patch

import pytest

from src.services.agents.config import AgentConfig, ModelConfig
from src.services.agents.implementations.code_agent import CodeAgent, create_code_agent


class TestCodeAgent:
    @pytest.fixture
    def mock_config(self):
        return AgentConfig(
            name="TestCodeAgent",
            description="Test description",
            llm_config=ModelConfig(provider="google", model_name="gemini-pro", api_key="test-key"),
        )

    @pytest.fixture
    def agent(self, mock_config):
        agent = CodeAgent(mock_config)
        agent.client = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_execute_generate(self, agent):
        input_data = {"task": "generate", "language": "python", "requirements": "Print hello world"}

        mock_response = MagicMock()
        mock_response.text = "print('Hello World')"
        agent.client.models.generate_content.return_value = mock_response

        result = await agent.execute(input_data)

        assert result["task"] == "generate"
        assert result["result"] == "print('Hello World')"
        agent.client.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_review(self, agent):
        input_data = {"task": "review", "language": "python", "code": "print('hello')"}

        mock_response = MagicMock()
        mock_response.text = "Code looks good"
        agent.client.models.generate_content.return_value = mock_response

        result = await agent.execute(input_data)

        assert result["task"] == "review"
        assert result["result"] == "Code looks good"

    @pytest.mark.asyncio
    async def test_execute_debug(self, agent):
        input_data = {"task": "debug", "language": "python", "code": "print(undefined_var)", "context": "NameError"}

        mock_response = MagicMock()
        mock_response.text = "Fixed code"
        agent.client.models.generate_content.return_value = mock_response

        result = await agent.execute(input_data)

        assert result["task"] == "debug"
        assert result["result"] == "Fixed code"

    @pytest.mark.asyncio
    async def test_execute_explain(self, agent):
        input_data = {"task": "explain", "language": "python", "code": "x = 1"}

        mock_response = MagicMock()
        mock_response.text = "Explanation"
        agent.client.models.generate_content.return_value = mock_response

        result = await agent.execute(input_data)

        assert result["task"] == "explain"
        assert result["result"] == "Explanation"

    @pytest.mark.asyncio
    async def test_execute_invalid_task(self, agent):
        input_data = {"task": "unknown", "requirements": "req"}
        with pytest.raises(ValueError, match="Unknown task type"):
            await agent.execute(input_data)

    @pytest.mark.asyncio
    async def test_execute_missing_inputs(self, agent):
        input_data = {"task": "generate"}  # Missing requirements/code
        with pytest.raises(ValueError, match="Either 'requirements' or 'code' must be provided"):
            await agent.execute(input_data)

    @pytest.mark.asyncio
    async def test_execute_no_client(self, mock_config):
        agent = CodeAgent(mock_config)
        # client is None
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await agent.execute({})

    def test_create_code_agent(self):
        with patch("src.services.agents.implementations.code_agent.CodeAgent") as MockAgent:
            create_code_agent("test-key")
            MockAgent.assert_called_once()
            MockAgent.return_value.initialize_client.assert_called_with("test-key")
