"""Factory for creating vector database providers."""

import logging
from typing import Any

from src.models.knowledge_base import VectorDBProvider as VectorDBProviderEnum

from .base_vector_db import BaseVectorDBProvider
from .pinecone_provider import PineconeProvider
from .qdrant_provider import QdrantProvider

logger = logging.getLogger(__name__)


class VectorDBProviderFactory:
    """Factory class for creating vector database providers."""

    _providers = {
        VectorDBProviderEnum.QDRANT: QdrantProvider,
        VectorDBProviderEnum.PINECONE: PineconeProvider,
        # Add more providers as they are implemented
        # VectorDBProviderEnum.WEAVIATE: WeaviateProvider,
        # VectorDBProviderEnum.CHROMA: ChromaProvider,
        # VectorDBProviderEnum.MILVUS: MilvusProvider,
    }

    @classmethod
    def create(cls, provider_type: VectorDBProviderEnum, config: dict[str, Any]) -> BaseVectorDBProvider:
        """
        Create a vector database provider instance.

        Args:
            provider_type: Type of vector DB provider
            config: Provider-specific configuration

        Returns:
            Vector DB provider instance

        Raises:
            ValueError: If provider type is not supported
        """
        provider_class = cls._providers.get(provider_type)

        if not provider_class:
            raise ValueError(
                f"Unsupported vector DB provider: {provider_type}. Supported providers: {list(cls._providers.keys())}"
            )

        logger.info(f"Creating {provider_type} provider")
        return provider_class(config)

    @classmethod
    def register_provider(cls, provider_type: VectorDBProviderEnum, provider_class: type) -> None:
        """
        Register a new vector DB provider.

        Args:
            provider_type: Type of provider
            provider_class: Provider class
        """
        if not issubclass(provider_class, BaseVectorDBProvider):
            raise ValueError("Provider class must inherit from BaseVectorDBProvider")

        cls._providers[provider_type] = provider_class
        logger.info(f"Registered provider: {provider_type}")

    @classmethod
    def get_supported_providers(cls) -> list:
        """
        Get list of supported provider types.

        Returns:
            List of supported provider types
        """
        return list(cls._providers.keys())

    @classmethod
    def is_provider_supported(cls, provider_type: VectorDBProviderEnum) -> bool:
        """
        Check if a provider type is supported.

        Args:
            provider_type: Provider type to check

        Returns:
            True if supported, False otherwise
        """
        return provider_type in cls._providers
