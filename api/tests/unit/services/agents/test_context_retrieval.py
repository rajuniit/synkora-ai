"""Tests for context_retrieval.py."""

from unittest.mock import Mock

import pytest


class TestContextRetrieval:
    """Tests for ContextRetrieval class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        assert service.vector_db is None
        assert service.embedding_service is None
        assert service.local_cache == {}

    def test_init_with_dependencies(self):
        """Test initialization with vector DB and embedding service."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_embedding = Mock()

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        assert service.vector_db is mock_vector_db
        assert service.embedding_service is mock_embedding


class TestStoreContext:
    """Tests for store_context method."""

    @pytest.mark.asyncio
    async def test_store_context_locally_no_vector_db(self):
        """Test storing context locally when no vector DB."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]

        storage_id = await service.store_context(
            conversation_id="conv-123", messages=messages, metadata={"source": "test"}
        )

        assert storage_id is not None
        assert "conv-123" in service.local_cache
        assert len(service.local_cache["conv-123"]) == 1
        assert service.local_cache["conv-123"][0]["messages"] == messages

    @pytest.mark.asyncio
    async def test_store_context_with_vector_db(self):
        """Test storing context with vector DB."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_vector_db.insert = Mock()

        mock_embedding = Mock()
        mock_embedding.embed_texts = Mock(return_value=[[0.1, 0.2], [0.3, 0.4]])

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]

        storage_id = await service.store_context(conversation_id="conv-456", messages=messages)

        assert storage_id is not None
        assert mock_embedding.embed_texts.called
        assert mock_vector_db.insert.call_count == 2

    @pytest.mark.asyncio
    async def test_store_context_fallback_on_exception(self):
        """Test falling back to local storage on exception."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_embedding = Mock()
        mock_embedding.embed_texts = Mock(side_effect=Exception("Embedding error"))

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        messages = [{"role": "user", "content": "Test"}]

        storage_id = await service.store_context(conversation_id="conv-789", messages=messages)

        # Should fall back to local storage
        assert storage_id is not None
        assert "conv-789" in service.local_cache


class TestStoreLocally:
    """Tests for _store_locally method."""

    def test_store_locally_new_conversation(self):
        """Test storing to new conversation."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        messages = [{"role": "user", "content": "Hello"}]
        storage_id = service._store_locally("conv-new", messages, {"key": "value"})

        assert storage_id is not None
        assert "conv-new" in service.local_cache
        assert len(service.local_cache["conv-new"]) == 1
        assert service.local_cache["conv-new"][0]["metadata"] == {"key": "value"}

    def test_store_locally_existing_conversation(self):
        """Test storing to existing conversation."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store first set
        messages1 = [{"role": "user", "content": "Hello"}]
        service._store_locally("conv-existing", messages1, {})

        # Store second set
        messages2 = [{"role": "user", "content": "Another message"}]
        service._store_locally("conv-existing", messages2, {})

        assert len(service.local_cache["conv-existing"]) == 2

    def test_store_locally_without_metadata(self):
        """Test storing without metadata."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        messages = [{"role": "user", "content": "Test"}]
        storage_id = service._store_locally("conv-no-meta", messages, None)

        assert storage_id is not None
        assert service.local_cache["conv-no-meta"][0]["metadata"] == {}


class TestRetrieveRelevantContext:
    """Tests for retrieve_relevant_context method."""

    @pytest.mark.asyncio
    async def test_retrieve_locally_no_vector_db(self):
        """Test retrieving from local cache when no vector DB."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store some context first
        messages = [
            {"role": "user", "content": "What is Python programming?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]
        await service.store_context("conv-search", messages)

        # Retrieve
        results = await service.retrieve_relevant_context(
            conversation_id="conv-search", query="Python programming", top_k=5
        )

        assert len(results) > 0
        assert results[0]["score"] > 0

    @pytest.mark.asyncio
    async def test_retrieve_with_vector_db(self):
        """Test retrieving with vector DB."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_vector_db.search = Mock(
            return_value=[
                {
                    "score": 0.9,
                    "payload": {"text": "user: Hello world", "message_index": 0, "timestamp": "2024-01-01T00:00:00"},
                }
            ]
        )

        mock_embedding = Mock()
        mock_embedding.embed_texts = Mock(return_value=[[0.1, 0.2]])

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        results = await service.retrieve_relevant_context(
            conversation_id="conv-vdb", query="Hello", top_k=5, min_score=0.7
        )

        assert len(results) == 1
        assert results[0]["score"] == 0.9
        assert "Hello world" in results[0]["text"]

    @pytest.mark.asyncio
    async def test_retrieve_fallback_on_exception(self):
        """Test falling back to local on exception."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_embedding = Mock()
        mock_embedding.embed_texts = Mock(side_effect=Exception("Search error"))

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        # Store locally
        service._store_locally("conv-fallback", [{"role": "user", "content": "test query"}])

        results = await service.retrieve_relevant_context(conversation_id="conv-fallback", query="test", top_k=5)

        # Should fall back to local and find match
        assert len(results) > 0


class TestRetrieveLocally:
    """Tests for _retrieve_locally method."""

    def test_retrieve_locally_no_conversation(self):
        """Test retrieving from nonexistent conversation."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        results = service._retrieve_locally("nonexistent", "query", 5)

        assert results == []

    def test_retrieve_locally_with_matches(self):
        """Test retrieving with keyword matches."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store test data
        service._store_locally(
            "conv-match",
            [
                {"role": "user", "content": "Tell me about Python programming"},
                {"role": "assistant", "content": "Python is great for scripting"},
                {"role": "user", "content": "What about Java?"},
            ],
        )

        results = service._retrieve_locally("conv-match", "Python programming", 5)

        # Should find Python-related messages
        assert len(results) > 0
        assert any("Python" in r["text"] for r in results)

    def test_retrieve_locally_respects_top_k(self):
        """Test that top_k limit is respected."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store many messages
        messages = [{"role": "user", "content": f"Test message {i}"} for i in range(10)]
        service._store_locally("conv-topk", messages)

        results = service._retrieve_locally("conv-topk", "Test message", top_k=3)

        assert len(results) <= 3

    def test_retrieve_locally_sorts_by_score(self):
        """Test that results are sorted by score."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        messages = [
            {"role": "user", "content": "apple banana cherry"},
            {"role": "user", "content": "apple"},
            {"role": "user", "content": "apple banana"},
        ]
        service._store_locally("conv-sort", messages)

        results = service._retrieve_locally("conv-sort", "apple banana cherry", 5)

        # Results should be sorted by score (more matches = higher score)
        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]


class TestGetConversationSummary:
    """Tests for get_conversation_summary method."""

    @pytest.mark.asyncio
    async def test_get_summary_existing(self):
        """Test getting summary of existing conversation."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store some data
        await service.store_context(
            "conv-summary", [{"role": "user", "content": "Msg 1"}, {"role": "assistant", "content": "Msg 2"}]
        )
        await service.store_context("conv-summary", [{"role": "user", "content": "Msg 3"}])

        summary = await service.get_conversation_summary("conv-summary")

        assert summary is not None
        assert summary["conversation_id"] == "conv-summary"
        assert summary["total_messages"] == 3
        assert summary["storage_count"] == 2
        assert "first_stored" in summary
        assert "last_stored" in summary

    @pytest.mark.asyncio
    async def test_get_summary_nonexistent(self):
        """Test getting summary of nonexistent conversation."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        summary = await service.get_conversation_summary("nonexistent")

        assert summary is None


class TestClearConversation:
    """Tests for clear_conversation method."""

    def test_clear_local_only(self):
        """Test clearing conversation from local cache only."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store data
        service._store_locally("conv-clear", [{"role": "user", "content": "Test"}])

        result = service.clear_conversation("conv-clear")

        assert result is True
        assert "conv-clear" not in service.local_cache

    def test_clear_with_vector_db(self):
        """Test clearing conversation with vector DB."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_vector_db.delete_collection = Mock()

        service = ContextRetrieval(vector_db=mock_vector_db)

        # Store locally too
        service._store_locally("conv-clear-vdb", [{"role": "user", "content": "Test"}])

        result = service.clear_conversation("conv-clear-vdb")

        assert result is True
        mock_vector_db.delete_collection.assert_called_once_with("context_conv-clear-vdb")
        assert "conv-clear-vdb" not in service.local_cache

    def test_clear_handles_exception(self):
        """Test clearing handles exceptions gracefully."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_vector_db.delete_collection = Mock(side_effect=Exception("Delete error"))

        service = ContextRetrieval(vector_db=mock_vector_db)

        result = service.clear_conversation("conv-error")

        assert result is False


class TestGetStats:
    """Tests for get_stats method."""

    def test_get_stats_empty(self):
        """Test getting stats with no data."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        stats = service.get_stats()

        assert stats["total_conversations"] == 0
        assert stats["total_stored_items"] == 0
        assert stats["has_vector_db"] is False
        assert stats["has_embedding_service"] is False
        assert stats["storage_mode"] == "local_cache"

    def test_get_stats_with_data(self):
        """Test getting stats with stored data."""
        from src.services.agents.context_retrieval import ContextRetrieval

        service = ContextRetrieval()

        # Store some data
        service._store_locally("conv1", [{"role": "user", "content": "Test"}])
        service._store_locally("conv1", [{"role": "user", "content": "Test 2"}])
        service._store_locally("conv2", [{"role": "user", "content": "Test 3"}])

        stats = service.get_stats()

        assert stats["total_conversations"] == 2
        assert stats["total_stored_items"] == 3

    def test_get_stats_with_vector_db(self):
        """Test getting stats with vector DB configured."""
        from src.services.agents.context_retrieval import ContextRetrieval

        mock_vector_db = Mock()
        mock_embedding = Mock()

        service = ContextRetrieval(vector_db=mock_vector_db, embedding_service=mock_embedding)

        stats = service.get_stats()

        assert stats["has_vector_db"] is True
        assert stats["has_embedding_service"] is True
        assert stats["storage_mode"] == "vector_db"
