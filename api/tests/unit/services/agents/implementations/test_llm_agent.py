from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.agents.config import AgentConfig, ModelConfig
from src.services.agents.implementations.llm_agent import LLMAgent, create_llm_agent


class TestLLMAgent:
    @pytest.fixture
    def mock_llm_config(self):
        return ModelConfig(
            provider="google", model_name="gemini-pro", api_key="test-key", temperature=0.7, max_tokens=100
        )

    @pytest.fixture
    def agent_config(self, mock_llm_config):
        return AgentConfig(
            name="TestAgent", description="Test Description", system_prompt="System Prompt", llm_config=mock_llm_config
        )

    @pytest.fixture
    def agent(self, agent_config):
        agent = LLMAgent(agent_config)
        agent.llm_client = MagicMock()
        agent.llm_client.generate_content = AsyncMock()
        return agent

    @pytest.mark.asyncio
    async def test_execute_success(self, agent):
        agent.llm_client.generate_content.return_value = "Generated Response"

        input_data = {"prompt": "User Question", "context": "Context Info", "temperature": 0.5, "max_tokens": 50}

        result = await agent.execute(input_data)

        expected_prompt = "System Prompt\n\nContext: Context Info\n\nUser: User Question"

        agent.llm_client.generate_content.assert_called_once_with(
            prompt=expected_prompt, temperature=0.5, max_tokens=50
        )

        assert result["response"] == "Generated Response"
        assert result["model"] == "gemini-pro"
        assert result["provider"] == "google"
        assert result["prompt_length"] == len(expected_prompt)
        assert result["response_length"] == len("Generated Response")

    @pytest.mark.asyncio
    async def test_execute_default_params(self, agent):
        agent.llm_client.generate_content.return_value = "Response"

        input_data = {"prompt": "Question"}

        await agent.execute(input_data)

        expected_prompt = "System Prompt\n\nUser: Question"

        # Should use defaults from config
        agent.llm_client.generate_content.assert_called_once_with(
            prompt=expected_prompt, temperature=0.7, max_tokens=100
        )

    @pytest.mark.asyncio
    async def test_execute_missing_prompt(self, agent):
        with pytest.raises(ValueError, match="'prompt' is required"):
            await agent.execute({})

    @pytest.mark.asyncio
    async def test_execute_client_not_initialized(self, agent_config):
        # Create agent without setting llm_client
        agent = LLMAgent(agent_config)

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await agent.execute({"prompt": "test"})

    @pytest.mark.asyncio
    async def test_execute_client_error(self, agent):
        agent.llm_client.generate_content.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await agent.execute({"prompt": "test"})

    def test_create_llm_agent_helper(self):
        with patch("src.services.agents.implementations.llm_agent.LLMAgent") as MockAgent:
            mock_instance = MockAgent.return_value

            create_llm_agent("api-key", "custom prompt")

            MockAgent.assert_called_once()
            # Verify config passed to constructor
            config = MockAgent.call_args[0][0]
            assert isinstance(config, AgentConfig)
            assert config.name == "llm_agent"
            assert config.system_prompt == "custom prompt"

            mock_instance.initialize_client.assert_called_with("api-key")
