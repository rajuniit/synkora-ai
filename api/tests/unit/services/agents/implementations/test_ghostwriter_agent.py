from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.writing_style_profile import WritingStyleProfile
from src.services.agents.config import AgentConfig, ModelConfig
from src.services.agents.implementations.ghostwriter_agent import GhostwriterAgent, create_ghostwriter_agent


class TestGhostwriterAgent:
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
        agent.tenant_id = "tenant-id"
        agent.name = "Ghostwriter"
        agent.knowledge_bases = ["kb1"]  # Must be truthy for context retrieval
        return agent

    @pytest.fixture
    def mock_config(self):
        return AgentConfig(
            name="Ghostwriter",
            description="Ghostwriter Agent",
            llm_config=ModelConfig(provider="google", model_name="gemini-pro", api_key="test-key"),
        )

    @pytest.fixture
    def agent(self, mock_config, mock_agent_model, mock_db_session, mock_google_client):
        with (
            patch("src.services.agents.implementations.ghostwriter_agent.RAGService"),
            patch("src.services.agents.implementations.ghostwriter_agent.WritingStyleAnalyzer"),
        ):
            agent = GhostwriterAgent(
                config=mock_config,
                agent_model=mock_agent_model,
                db_session=mock_db_session,
                google_client=mock_google_client,
            )
            agent.llm_client = AsyncMock()
            agent.llm_client.generate_content = AsyncMock(return_value="Generated draft")

            # Mock internal services
            agent.rag_service.augment_prompt_with_context = AsyncMock(
                return_value={"context": "Retrieved Context", "sources": ["source1"], "num_sources": 1}
            )

            return agent

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, mock_db_session):
        input_data = {"person_identifier": "test@example.com", "topic": "Project Update", "save_draft": True}

        # Mock style profile
        mock_profile = MagicMock(spec=WritingStyleProfile)
        mock_profile.id = "profile-id"
        mock_profile.confidence_score = 0.9
        mock_profile.tone_characteristics = {"formal_score": 0.8}
        mock_profile.vocabulary_patterns = {}
        mock_profile.sentence_metrics = {}
        mock_profile.communication_patterns = {}

        # Mock getting style profile - db.execute() returns a result object
        # whose scalar_one_or_none() is synchronous
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_db_session.execute.return_value = mock_result

        result = await agent.execute(input_data)

        assert result["draft"] == "Generated draft"
        assert result["person_identifier"] == "test@example.com"
        assert result["sources"] == ["source1"]

        agent.llm_client.generate_content.assert_called_once()
        mock_db_session.add.assert_called_once()  # Draft saved

    @pytest.mark.asyncio
    async def test_execute_no_profile(self, agent, mock_db_session):
        input_data = {"person_identifier": "unknown@example.com", "topic": "Topic"}

        # Mock db.execute() to return a result with no profile
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="No style profile found"):
            await agent.execute(input_data)

    @pytest.mark.asyncio
    async def test_execute_missing_inputs(self, agent):
        with pytest.raises(ValueError, match="'person_identifier' is required"):
            await agent.execute({"topic": "Topic"})

        with pytest.raises(ValueError, match="'topic' is required"):
            await agent.execute({"person_identifier": "p"})

    @pytest.mark.asyncio
    async def test_execute_no_client(self, agent):
        agent.llm_client = None
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await agent.execute({})

    def test_build_style_instructions(self, agent):
        profile = MagicMock()
        profile.tone_characteristics = {"formal_score": 0.9}
        profile.vocabulary_patterns = {"common_phrases": ["a", "b"]}
        profile.sentence_metrics = {"avg_sentence_length": 20}
        profile.communication_patterns = {"opening_style": "Hello", "closing_style": "Bye"}

        instructions = agent._build_style_instructions(profile, None)
        assert "Tone: formal" in instructions
        assert "Common phrases: a, b" in instructions
        assert "Opening style: Hello" in instructions

    def test_describe_tone(self, agent):
        tone = {"formal_score": 0.9, "professional_score": 0.8}
        desc = agent._describe_tone(tone, None)
        assert "formal" in desc
        assert "professional" in desc

        desc_adj = agent._describe_tone(tone, "more_casual")
        # Formal should decrease
        # 0.9 - 0.2 = 0.7 -> still formal (>0.6)
        assert "formal" in desc_adj

    def test_cleanup(self, agent):
        agent.cleanup()
        agent.rag_service.cleanup.assert_called_once()

    def test_create_ghostwriter_agent(self, mock_agent_model, mock_db_session, mock_google_client):
        with patch("src.services.agents.implementations.ghostwriter_agent.GhostwriterAgent") as MockAgent:
            mock_agent_model.description = None  # Test default description
            mock_agent_model.system_prompt = None  # Test default prompt

            create_ghostwriter_agent(mock_agent_model, mock_db_session, mock_google_client, "api-key")

            MockAgent.assert_called_once()
            MockAgent.return_value.initialize_client.assert_called_with("api-key")
