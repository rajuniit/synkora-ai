"""Qdrant vector database provider implementation."""

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from .base_vector_db import BaseVectorDBProvider

logger = logging.getLogger(__name__)


class QdrantProvider(BaseVectorDBProvider):
    """Qdrant vector database provider implementation."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Qdrant provider.

        Args:
            config: Configuration dictionary with keys:
                - host: Qdrant host (default: localhost)
                - port: Qdrant port (default: 6333)
                - api_key: Optional API key
                - url: Optional full URL (overrides host/port)
        """
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6333)
        self.api_key = config.get("api_key")
        self.url = config.get("url")

    def connect(self) -> None:
        """Establish connection to Qdrant."""
        try:
            # Configure timeout to prevent hanging connections in K8s
            timeout = self.config.get("timeout", 30)  # 30 seconds default

            if self.url:
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=timeout,
                )
            else:
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                    timeout=timeout,
                )
            logger.info(f"Connected to Qdrant at {self.url or f'{self.host}:{self.port}'} (timeout={timeout}s)")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Failed to connect to Qdrant: {e}")

    def disconnect(self) -> None:
        """Close connection to Qdrant."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Disconnected from Qdrant")

    def create_collection(
        self, collection_name: str, dimension: int, distance_metric: str = "cosine", **kwargs
    ) -> None:
        """Create a new collection in Qdrant."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        # Map distance metric
        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot_product": Distance.DOT,
        }
        distance = distance_map.get(distance_metric.lower(), Distance.COSINE)

        try:
            self.client.create_collection(
                collection_name=collection_name, vectors_config=VectorParams(size=dimension, distance=distance)
            )
            logger.info(f"Created collection '{collection_name}' with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise ValueError(f"Failed to create collection: {e}")

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection from Qdrant."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    def add_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """Add vectors to a collection."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        points = []
        ids = []

        for vector_data in vectors:
            # Generate ID if not provided
            vector_id = vector_data.get("id") or str(uuid.uuid4())
            ids.append(vector_id)

            point = PointStruct(id=vector_id, vector=vector_data["vector"], payload=vector_data.get("payload", {}))
            points.append(point)

        try:
            self.client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Added {len(points)} vectors to '{collection_name}'")
            return ids
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            raise ValueError(f"Failed to add vectors: {e}")

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        # Build filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                query_filter = Filter(must=conditions)

        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            return [{"id": str(result.id), "score": result.score, "payload": result.payload} for result in results]
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors from a collection."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        try:
            self.client.delete(collection_name=collection_name, points_selector=vector_ids)
            logger.info(f"Deleted {len(vector_ids)} vectors from '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise

    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Update a vector's data or payload."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        try:
            if vector is not None:
                # Update vector
                point = PointStruct(id=vector_id, vector=vector, payload=payload or {})
                self.client.upsert(collection_name=collection_name, points=[point])
            elif payload is not None:
                # Update only payload
                self.client.set_payload(collection_name=collection_name, payload=payload, points=[vector_id])
            logger.info(f"Updated vector '{vector_id}' in '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to update vector: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get information about a collection."""
        if not self.client:
            raise ConnectionError("Not connected to Qdrant")

        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "dimension": info.config.params.vectors.size,
                "vector_count": info.points_count,
                "distance_metric": info.config.params.vectors.distance.name.lower(),
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise

    def health_check(self) -> bool:
        """Check if Qdrant is healthy and accessible."""
        if not self.client:
            return False

        try:
            # Try to get collections list
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
