"""Pinecone vector database provider implementation."""

import logging
import os
import uuid
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from .base_vector_db import BaseVectorDBProvider

logger = logging.getLogger(__name__)


class PineconeProvider(BaseVectorDBProvider):
    """Pinecone vector database provider implementation."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Pinecone provider.

        Args:
            config: Configuration dictionary with keys:
                - api_key: Pinecone API key (or from PINECONE_API_KEY env)
                - environment: Pinecone environment (default: us-east-1)
                - cloud: Cloud provider (default: aws)
        """
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("PINECONE_API_KEY")
        self.environment = config.get("environment") or os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.cloud = config.get("cloud") or os.getenv("PINECONE_CLOUD", "aws")

        if not self.api_key:
            raise ValueError("Pinecone API key is required")

    def connect(self) -> None:
        """Establish connection to Pinecone."""
        try:
            self.client = Pinecone(api_key=self.api_key)
            logger.info(f"Connected to Pinecone (environment: {self.environment})")
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise ConnectionError(f"Failed to connect to Pinecone: {e}")

    def disconnect(self) -> None:
        """Close connection to Pinecone."""
        # Pinecone client doesn't require explicit disconnection
        self.client = None
        logger.info("Disconnected from Pinecone")

    def create_collection(
        self, collection_name: str, dimension: int, distance_metric: str = "cosine", **kwargs
    ) -> None:
        """Create a new index in Pinecone."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        # Map distance metric
        metric_map = {
            "cosine": "cosine",
            "euclidean": "euclidean",
            "dot_product": "dotproduct",
        }
        metric = metric_map.get(distance_metric.lower(), "cosine")

        try:
            self.client.create_index(
                name=collection_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=self.cloud, region=self.environment),
            )
            logger.info(f"Created Pinecone index '{collection_name}' with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise ValueError(f"Failed to create index: {e}")

    def delete_collection(self, collection_name: str) -> None:
        """Delete an index from Pinecone."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            self.client.delete_index(collection_name)
            logger.info(f"Deleted Pinecone index '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            raise

    def collection_exists(self, collection_name: str) -> bool:
        """Check if an index exists."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            indexes = self.client.list_indexes()
            index_names = [idx.name for idx in indexes]
            return collection_name in index_names
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    def add_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
        namespace: str | None = None,
    ) -> list[str]:
        """Add vectors to an index with optional namespace."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            index = self.client.Index(collection_name)

            # Prepare vectors for upsert
            vectors_to_upsert = []
            ids = []

            for vector_data in vectors:
                # Generate ID if not provided
                vector_id = vector_data.get("id") or str(uuid.uuid4())
                ids.append(vector_id)

                vectors_to_upsert.append(
                    {"id": vector_id, "values": vector_data["vector"], "metadata": vector_data.get("payload", {})}
                )

            # Upsert in batches of 100 (Pinecone recommendation)
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i : i + batch_size]
                if namespace:
                    index.upsert(vectors=batch, namespace=namespace)
                else:
                    index.upsert(vectors=batch)

            namespace_info = f" in namespace '{namespace}'" if namespace else ""
            logger.info(f"Added {len(ids)} vectors to Pinecone index '{collection_name}'{namespace_info}")
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
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors with optional namespace."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            index = self.client.Index(collection_name)

            # Perform search
            query_params = {"vector": query_vector, "top_k": limit, "filter": filters, "include_metadata": True}
            if namespace:
                query_params["namespace"] = namespace

            results = index.query(**query_params)

            # Convert to standard format and apply score threshold
            search_results = []
            for match in results.matches:
                if score_threshold is None or match.score >= score_threshold:
                    search_results.append({"id": match.id, "score": match.score, "payload": match.metadata})

            namespace_info = f" in namespace '{namespace}'" if namespace else ""
            logger.info(f"Found {len(search_results)} results in Pinecone{namespace_info}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise

    def delete_vectors(
        self,
        collection_name: str,
        vector_ids: list[str],
        namespace: str | None = None,
    ) -> None:
        """Delete vectors from an index with optional namespace."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            index = self.client.Index(collection_name)
            if namespace:
                index.delete(ids=vector_ids, namespace=namespace)
            else:
                index.delete(ids=vector_ids)

            namespace_info = f" from namespace '{namespace}'" if namespace else ""
            logger.info(f"Deleted {len(vector_ids)} vectors from Pinecone index '{collection_name}'{namespace_info}")
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
            raise ConnectionError("Not connected to Pinecone")

        try:
            index = self.client.Index(collection_name)

            if vector is not None:
                # Update vector and metadata
                index.upsert(vectors=[{"id": vector_id, "values": vector, "metadata": payload or {}}])
            elif payload is not None:
                # Pinecone requires fetching the vector first to update only metadata
                fetch_response = index.fetch(ids=[vector_id])

                if vector_id in fetch_response.vectors:
                    vector_data = fetch_response.vectors[vector_id]
                    index.upsert(vectors=[{"id": vector_id, "values": vector_data.values, "metadata": payload}])
                else:
                    raise ValueError(f"Vector {vector_id} not found")

            logger.info(f"Updated vector '{vector_id}' in Pinecone index '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to update vector: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get information about an index."""
        if not self.client:
            raise ConnectionError("Not connected to Pinecone")

        try:
            index = self.client.Index(collection_name)
            stats = index.describe_index_stats()

            # Get index description for dimension and metric
            index_desc = self.client.describe_index(collection_name)

            return {
                "name": collection_name,
                "dimension": index_desc.dimension,
                "vector_count": stats.total_vector_count,
                "distance_metric": index_desc.metric,
            }
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            raise

    def health_check(self) -> bool:
        """Check if Pinecone is healthy and accessible."""
        if not self.client:
            return False

        try:
            # Try to list indexes
            self.client.list_indexes()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
