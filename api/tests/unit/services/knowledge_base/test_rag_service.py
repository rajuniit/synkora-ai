from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.agent_knowledge_base import AgentKnowledgeBase
from src.models.document import Document
from src.models.knowledge_base import EmbeddingProvider, KnowledgeBase, VectorDBProvider
from src.services.knowledge_base.rag_service import RAGService


class TestRAGService:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_google_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_vector_factory(self):
        with patch("src.services.knowledge_base.rag_service.VectorDBProviderFactory") as mock:
            yield mock

    @pytest.fixture
    def mock_embedding_service(self):
        with patch("src.services.knowledge_base.rag_service.EmbeddingService") as mock:
            yield mock

    @pytest.fixture
    def mock_s3_service(self):
        with patch("src.services.knowledge_base.rag_service.S3StorageService") as mock:
            yield mock

    @pytest.fixture
    def mock_langfuse(self):
        with patch("src.services.knowledge_base.rag_service.LangfuseService") as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_db, mock_google_client, mock_langfuse):
        return RAGService(mock_db, mock_google_client)

    @pytest.fixture
    def mock_kb(self):
        kb = MagicMock(spec=KnowledgeBase)
        kb.id = 1
        kb.name = "Test KB"
        kb.vector_db_provider = VectorDBProvider.PINECONE
        kb.embedding_provider = EmbeddingProvider.OPENAI
        kb.embedding_model = "text-embedding-3-small"
        kb.get_vector_db_config_decrypted.return_value = {"api_key": "key", "index_name": "idx"}
        kb.get_embedding_config_decrypted.return_value = {"api_key": "key"}
        kb.vector_db_config = {"index_name": "idx"}
        kb.embedding_config = {"dimension": 1536}
        kb.chunk_size = 1000
        kb.chunk_overlap = 100
        return kb

    def test_get_vector_db(self, service, mock_kb, mock_vector_factory):
        # First call creates
        provider = MagicMock()
        mock_vector_factory.create.return_value = provider

        result = service.get_vector_db(mock_kb)
        assert result == provider
        mock_vector_factory.create.assert_called_once()
        provider.connect.assert_called_once()

        # Second call uses cache
        result2 = service.get_vector_db(mock_kb)
        assert result2 == provider
        assert mock_vector_factory.create.call_count == 1

    def test_get_embedding_service(self, service, mock_kb, mock_embedding_service):
        # First call creates
        embed_svc = mock_embedding_service.return_value

        result = service.get_embedding_service(mock_kb)
        assert result == embed_svc
        mock_embedding_service.assert_called_once()

        # Second call uses cache
        result2 = service.get_embedding_service(mock_kb)
        assert result2 == embed_svc
        assert mock_embedding_service.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_embedding(self, service, mock_kb):
        service.get_embedding_service = MagicMock()
        embed_svc = service.get_embedding_service.return_value
        embed_svc.embed_text.return_value = [0.1, 0.2]

        vec = await service.generate_embedding("text", mock_kb)
        assert vec == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_enrich_with_document_metadata(self, service, mock_s3_service):
        mock_s3_service.return_value.generate_presigned_url.return_value = "url"

        results = [{"payload": {"doc_id": "123"}}]

        mock_doc = MagicMock(spec=Document)
        mock_doc.id = "123"
        mock_doc.title = "Doc 1"
        mock_doc.s3_key = "key"
        mock_doc.metadata = {}
        mock_doc.created_at = datetime.now()

        # Mock db.execute for async select query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_doc]
        service.db.execute = AsyncMock(return_value=mock_result)

        enriched = await service._enrich_with_document_metadata(results)

        assert "document" in enriched[0]
        assert enriched[0]["document"]["title"] == "Doc 1"
        assert enriched[0]["document"]["presigned_url"] == "url"

    @pytest.mark.asyncio
    async def test_retrieve_context(self, service, mock_kb):
        mock_agent = MagicMock(spec=Agent)
        mock_agent.id = 1

        mock_agent_kb = MagicMock(spec=AgentKnowledgeBase)
        mock_agent_kb.knowledge_base = mock_kb
        mock_agent_kb.retrieval_config = {}
        mock_agent_kb.is_active = True

        # Mock db.execute for async select query with selectinload
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_agent_kb]
        service.db.execute = AsyncMock(return_value=mock_result)

        service.generate_embedding = AsyncMock(return_value=[0.1])

        mock_vector_db = MagicMock()
        mock_vector_db.search.return_value = [{"score": 0.9, "payload": {"text": "content"}}]
        service.get_vector_db = MagicMock(return_value=mock_vector_db)

        results = await service.retrieve_context("query", mock_agent)

        assert len(results) == 1
        assert results[0]["knowledge_base_id"] == mock_kb.id
        service.generate_embedding.assert_called()
        mock_vector_db.search.assert_called()

    def test_format_context_for_prompt(self, service):
        docs = [{"score": 0.9, "knowledge_base_name": "KB1", "payload": {"text": "Content 1", "source": "Source 1"}}]

        context = service.format_context_for_prompt(docs)
        assert "Content 1" in context
        assert "Source 1" in context
        assert "KB1" in context

    def test_format_sources_for_response(self, service):
        docs = [
            {
                "score": 0.9,
                "knowledge_base_name": "KB1",
                "payload": {"text": "Content 1", "source": "Source 1"},
                "document": {
                    "title": "Doc 1",
                    "source_type": "SLACK",
                    "metadata": {"channel": "general", "timestamp": "123"},
                },
            }
        ]

        sources = service.format_sources_for_response(docs)
        assert len(sources) == 1
        assert sources[0]["score"] == 0.9
        assert sources[0]["display"]["type"] == "Slack Message"
        assert sources[0]["display"]["channel"] == "general"

    @pytest.mark.asyncio
    async def test_augment_prompt_with_context(self, service):
        service.retrieve_context = AsyncMock(return_value=[{"payload": {"text": "Ctx"}}])
        service.format_context_for_prompt = MagicMock(return_value="Formatted Context")
        service.format_sources_for_response = MagicMock(return_value=[{"src": 1}])

        result = await service.augment_prompt_with_context("query", MagicMock())

        assert "Formatted Context" in result["augmented_prompt"]
        assert result["context"] == "Formatted Context"
        assert len(result["sources"]) == 1

    @pytest.mark.asyncio
    async def test_add_documents_to_knowledge_base(self, service, mock_kb):
        mock_vector_db = MagicMock()
        mock_vector_db.collection_exists.return_value = False
        service.get_vector_db = MagicMock(return_value=mock_vector_db)

        service.text_processor.chunk_text = MagicMock(return_value=["chunk1", "chunk2"])

        embed_svc = MagicMock()
        embed_svc.embed_texts.return_value = [[0.1], [0.2]]
        service.get_embedding_service = MagicMock(return_value=embed_svc)

        docs = [{"text": "doc content", "metadata": {"source": "file.txt"}, "id": "doc1"}]

        stats = await service.add_documents_to_knowledge_base(mock_kb, docs)

        assert stats["documents_added"] == 1
        assert stats["chunks_created"] == 2
        mock_vector_db.create_collection.assert_called()
        mock_vector_db.add_vectors.assert_called()
        service.db.commit.assert_called()

    def test_cleanup(self, service):
        mock_provider = MagicMock()
        service._vector_db_cache = {1: mock_provider}

        service.cleanup()

        mock_provider.disconnect.assert_called()
        assert len(service._vector_db_cache) == 0
