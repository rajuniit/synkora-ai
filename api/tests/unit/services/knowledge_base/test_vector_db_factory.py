"""Unit tests for VectorDBProviderFactory."""

from unittest.mock import patch

import pytest

from src.models.knowledge_base import VectorDBProvider as VectorDBProviderEnum
from src.services.knowledge_base.providers.base_vector_db import BaseVectorDBProvider
from src.services.knowledge_base.providers.vector_db_factory import VectorDBProviderFactory


# A concrete stub that satisfies the abstract interface for registration tests
class _StubProvider(BaseVectorDBProvider):
    def connect(self):
        pass

    def disconnect(self):
        pass

    def create_collection(self, collection_name, dimension, distance_metric="cosine", **kwargs):
        pass

    def delete_collection(self, collection_name):
        pass

    def collection_exists(self, collection_name):
        return False

    def add_vectors(self, collection_name, vectors):
        return []

    def search(self, collection_name, query_vector, limit=10, filters=None, score_threshold=None):
        return []

    def delete_vectors(self, collection_name, vector_ids):
        pass

    def update_vector(self, collection_name, vector_id, vector=None, payload=None):
        pass

    def get_collection_info(self, collection_name):
        return {}

    def health_check(self):
        return True


@pytest.mark.unit
class TestVectorDBProviderFactoryCreate:
    def test_qdrant_creates_qdrant_provider(self):
        from src.services.knowledge_base.providers.qdrant_provider import QdrantProvider

        with patch.object(QdrantProvider, "__init__", return_value=None):
            result = VectorDBProviderFactory.create(VectorDBProviderEnum.QDRANT, {})
        assert isinstance(result, QdrantProvider)

    def test_pinecone_creates_pinecone_provider(self):
        from src.services.knowledge_base.providers.pinecone_provider import PineconeProvider

        with patch.object(PineconeProvider, "__init__", return_value=None):
            result = VectorDBProviderFactory.create(VectorDBProviderEnum.PINECONE, {})
        assert isinstance(result, PineconeProvider)

    def test_unsupported_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported vector DB provider"):
            VectorDBProviderFactory.create(VectorDBProviderEnum.WEAVIATE, {})

    def test_error_message_lists_supported_providers(self):
        with pytest.raises(ValueError) as exc_info:
            VectorDBProviderFactory.create(VectorDBProviderEnum.CHROMA, {})
        # Supported providers listed in error
        assert "QDRANT" in str(exc_info.value) or "qdrant" in str(exc_info.value).lower()

    def test_config_passed_to_provider(self):
        from src.services.knowledge_base.providers.qdrant_provider import QdrantProvider

        config = {"url": "http://qdrant:6333", "collection": "test"}
        received = {}

        def capture_init(self, cfg):
            received["config"] = cfg

        with patch.object(QdrantProvider, "__init__", capture_init):
            VectorDBProviderFactory.create(VectorDBProviderEnum.QDRANT, config)

        assert received["config"] is config


@pytest.mark.unit
class TestVectorDBProviderFactoryGetSupported:
    def test_returns_list(self):
        result = VectorDBProviderFactory.get_supported_providers()
        assert isinstance(result, list)

    def test_qdrant_in_supported(self):
        assert VectorDBProviderEnum.QDRANT in VectorDBProviderFactory.get_supported_providers()

    def test_pinecone_in_supported(self):
        assert VectorDBProviderEnum.PINECONE in VectorDBProviderFactory.get_supported_providers()

    def test_at_least_two_providers(self):
        assert len(VectorDBProviderFactory.get_supported_providers()) >= 2


@pytest.mark.unit
class TestVectorDBProviderFactoryIsSupported:
    def test_qdrant_is_supported(self):
        assert VectorDBProviderFactory.is_provider_supported(VectorDBProviderEnum.QDRANT) is True

    def test_pinecone_is_supported(self):
        assert VectorDBProviderFactory.is_provider_supported(VectorDBProviderEnum.PINECONE) is True

    def test_weaviate_not_supported(self):
        assert VectorDBProviderFactory.is_provider_supported(VectorDBProviderEnum.WEAVIATE) is False

    def test_chroma_not_supported(self):
        assert VectorDBProviderFactory.is_provider_supported(VectorDBProviderEnum.CHROMA) is False


@pytest.mark.unit
class TestVectorDBProviderFactoryRegister:
    def setup_method(self):
        # Save original providers and restore after each test
        self._original = dict(VectorDBProviderFactory._providers)

    def teardown_method(self):
        VectorDBProviderFactory._providers = self._original

    def test_register_new_provider(self):
        VectorDBProviderFactory.register_provider(VectorDBProviderEnum.WEAVIATE, _StubProvider)
        assert VectorDBProviderFactory.is_provider_supported(VectorDBProviderEnum.WEAVIATE)

    def test_registered_provider_can_be_created(self):
        VectorDBProviderFactory.register_provider(VectorDBProviderEnum.WEAVIATE, _StubProvider)
        result = VectorDBProviderFactory.create(VectorDBProviderEnum.WEAVIATE, {})
        assert isinstance(result, _StubProvider)

    def test_non_subclass_raises_value_error(self):
        class NotAProvider:
            pass

        with pytest.raises(ValueError, match="must inherit from BaseVectorDBProvider"):
            VectorDBProviderFactory.register_provider(VectorDBProviderEnum.WEAVIATE, NotAProvider)

    def test_register_overwrites_existing(self):
        VectorDBProviderFactory.register_provider(VectorDBProviderEnum.WEAVIATE, _StubProvider)
        VectorDBProviderFactory.register_provider(VectorDBProviderEnum.WEAVIATE, _StubProvider)
        # No error; overwrite is permitted


@pytest.mark.unit
class TestBaseVectorDBBatchAdd:
    """Tests for the concrete batch_add_vectors method on BaseVectorDBProvider."""

    def setup_method(self):
        self.provider = _StubProvider({})

    def test_batch_add_calls_add_vectors_in_chunks(self):
        calls = []

        def fake_add(collection, batch):
            calls.append(len(batch))
            return [f"id-{i}" for i in range(len(batch))]

        self.provider.add_vectors = fake_add
        vectors = [{"id": str(i), "vector": [0.0]} for i in range(250)]
        ids = self.provider.batch_add_vectors("col", vectors, batch_size=100)

        # 250 vectors in batches of 100 → 3 calls: 100, 100, 50
        assert calls == [100, 100, 50]
        assert len(ids) == 250

    def test_batch_add_default_batch_size_100(self):
        calls = []

        def fake_add(collection, batch):
            calls.append(len(batch))
            return ["id"] * len(batch)

        self.provider.add_vectors = fake_add
        vectors = [{"id": str(i), "vector": [0.0]} for i in range(100)]
        self.provider.batch_add_vectors("col", vectors)
        assert len(calls) == 1
        assert calls[0] == 100

    def test_batch_add_empty_vectors_returns_empty(self):
        result = self.provider.batch_add_vectors("col", [])
        assert result == []

    def test_batch_add_collects_all_ids(self):
        def fake_add(collection, batch):
            return [f"id-{v['id']}" for v in batch]

        self.provider.add_vectors = fake_add
        vectors = [{"id": str(i), "vector": [0.0]} for i in range(5)]
        ids = self.provider.batch_add_vectors("col", vectors, batch_size=2)
        assert len(ids) == 5
