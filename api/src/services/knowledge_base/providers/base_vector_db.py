"""Base class for vector database providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseVectorDBProvider(ABC):
    """
    Abstract base class for vector database providers.

    All vector DB implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the vector DB provider.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.client = None

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the vector database.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the vector database."""
        pass

    @abstractmethod
    def create_collection(
        self, collection_name: str, dimension: int, distance_metric: str = "cosine", **kwargs
    ) -> None:
        """
        Create a new collection/index in the vector database.

        Args:
            collection_name: Name of the collection
            dimension: Dimension of the vectors
            distance_metric: Distance metric (cosine, euclidean, dot_product)
            **kwargs: Additional provider-specific parameters

        Raises:
            ValueError: If collection already exists or invalid parameters
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection/index from the vector database.

        Args:
            collection_name: Name of the collection to delete
        """
        pass

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        pass

    @abstractmethod
    def add_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """
        Add vectors to a collection.

        Args:
            collection_name: Name of the collection
            vectors: List of vector dictionaries with structure:
                {
                    "id": "optional_id",
                    "vector": [0.1, 0.2, ...],
                    "payload": {"key": "value", ...}
                }

        Returns:
            List of vector IDs

        Raises:
            ValueError: If collection doesn't exist or invalid data
        """
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection
            query_vector: Query vector
            limit: Maximum number of results
            filters: Optional filters to apply
            score_threshold: Minimum similarity score

        Returns:
            List of search results with structure:
                {
                    "id": "vector_id",
                    "score": 0.95,
                    "payload": {"key": "value", ...}
                }
        """
        pass

    @abstractmethod
    def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """
        Delete vectors from a collection.

        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to delete
        """
        pass

    @abstractmethod
    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Update a vector's data or payload.

        Args:
            collection_name: Name of the collection
            vector_id: ID of the vector to update
            vector: New vector data (optional)
            payload: New payload data (optional)
        """
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information:
                {
                    "name": "collection_name",
                    "dimension": 384,
                    "vector_count": 1000,
                    "distance_metric": "cosine"
                }
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the vector database is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def batch_add_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> list[str]:
        """
        Add vectors in batches for better performance.

        Args:
            collection_name: Name of the collection
            vectors: List of vectors to add
            batch_size: Number of vectors per batch

        Returns:
            List of all vector IDs
        """
        all_ids = []
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            ids = self.add_vectors(collection_name, batch)
            all_ids.extend(ids)
        return all_ids
