from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.services.agents.config import AgentConfig, ModelConfig
from src.services.agents.implementations.rag_agent import RAGAgent, create_rag_agent


class TestRAGAgent:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_google_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_agent_model(self):
        agent = MagicMock(spec=Agent)
        agent.id = "agent-id"
        agent.name = "RAGAgent"
        agent.knowledge_bases = ["kb1"]
        return agent

    @pytest.fixture
    def mock_config(self):
        return AgentConfig(
            name="RAGAgent",
            description="RAG Agent",
            system_prompt="System prompt",
            llm_config=ModelConfig(provider="google", model_name="gemini-pro", api_key="test-key"),
        )

    @pytest.fixture
    def agent(self, mock_config, mock_agent_model, mock_db_session, mock_google_client):
        with patch("src.services.agents.implementations.rag_agent.RAGService"):
            agent = RAGAgent(
                config=mock_config,
                agent_model=mock_agent_model,
                db_session=mock_db_session,
                google_client=mock_google_client,
            )
            agent.llm_client = AsyncMock()
            agent.llm_client.generate_content = AsyncMock(return_value="Response")

            # Mock internal services
            agent.rag_service.augment_prompt_with_context = AsyncMock(
                return_value={"context": "Context", "sources": ["source1"], "num_sources": 1}
            )

            return agent

    @pytest.mark.asyncio
    async def test_execute_with_rag(self, agent):
        input_data = {"prompt": "Question", "enable_rag": True}

        result = await agent.execute(input_data)

        assert result["response"] == "Response"
        assert result["rag_enabled"] is True
        assert result["num_sources"] == 1
        assert result["sources"] == ["source1"]

        agent.rag_service.augment_prompt_with_context.assert_called_once()
        agent.llm_client.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_without_rag(self, agent):
        input_data = {"prompt": "Question", "enable_rag": False}

        result = await agent.execute(input_data)

        assert result["response"] == "Response"
        assert result["rag_enabled"] is False
        assert result["num_sources"] == 0
        assert "sources" not in result

        agent.rag_service.augment_prompt_with_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_no_knowledge_bases(self, agent, mock_agent_model):
        mock_agent_model.knowledge_bases = []

        input_data = {"prompt": "Question", "enable_rag": True}

        result = await agent.execute(input_data)

        assert result["rag_enabled"] is False
        agent.rag_service.augment_prompt_with_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_missing_prompt(self, agent):
        with pytest.raises(ValueError, match="'prompt' is required"):
            await agent.execute({})

    @pytest.mark.asyncio
    async def test_execute_no_client(self, agent):
        agent.llm_client = None
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await agent.execute({"prompt": "hi"})

    def test_enable_rag(self, agent):
        agent.enable_rag(False)
        assert agent._enable_rag is False
        agent.enable_rag(True)
        assert agent._enable_rag is True

    def test_cleanup(self, agent):
        agent.cleanup()
        agent.rag_service.cleanup.assert_called_once()

    def test_create_rag_agent(self, mock_agent_model, mock_db_session, mock_google_client):
        with patch("src.services.agents.implementations.rag_agent.RAGAgent") as MockAgent:
            mock_agent_model.description = None
            mock_agent_model.system_prompt = None

            create_rag_agent(mock_agent_model, mock_db_session, mock_google_client, "api-key")

            MockAgent.assert_called_once()
            MockAgent.return_value.initialize_client.assert_called_with("api-key")
