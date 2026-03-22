from unittest.mock import MagicMock, patch

import pytest

from src.services.agents.config import AgentConfig, ModelConfig
from src.services.agents.implementations.research_agent import ResearchAgent, create_research_agent


class TestResearchAgent:
    @pytest.fixture
    def mock_config(self):
        return AgentConfig(
            name="ResearchAgent",
            description="Research Agent",
            llm_config=ModelConfig(provider="google", model_name="gemini-pro", api_key="test-key"),
        )

    @pytest.fixture
    def agent(self, mock_config):
        agent = ResearchAgent(mock_config)
        agent.client = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_execute_success(self, agent):
        input_data = {"query": "What is quantum computing?", "depth": "quick"}

        mock_response = MagicMock()
        mock_response.text = """
        # Findings
        Quantum computing uses qubits.
        
        # Summary
        It is fast.
        """
        agent.client.models.generate_content.return_value = mock_response

        result = await agent.execute(input_data)

        assert result["query"] == "What is quantum computing?"
        assert "Quantum computing uses qubits" in result["findings"]
        assert "It is fast" in result["summary"]
        assert result["depth"] == "quick"

        agent.client.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_query(self, agent):
        with pytest.raises(ValueError, match="'query' is required"):
            await agent.execute({})

    @pytest.mark.asyncio
    async def test_execute_no_client(self, mock_config):
        agent = ResearchAgent(mock_config)
        # client is None
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await agent.execute({"query": "q"})

    def test_extract_section(self, agent):
        text = """
        Some intro.
        # Findings
        Finding 1.
        Finding 2.
        # Summary
        This is summary.
        """

        # Note: _extract_section implementation might be simple and fragile
        # It splits by lines and looks for section name in line.

        findings = agent._extract_section(text, "findings")
        # Based on implementation:
        # starts collecting when line contains "findings"
        # stops when line starts with "#"
        assert "Finding 1" in findings
        assert "Finding 2" in findings

        summary = agent._extract_section(text, "summary")
        assert "This is summary" in summary

    def test_create_research_agent(self):
        with patch("src.services.agents.implementations.research_agent.ResearchAgent") as MockAgent:
            create_research_agent("test-key")
            MockAgent.assert_called_once()
            MockAgent.return_value.initialize_client.assert_called_with("test-key")
