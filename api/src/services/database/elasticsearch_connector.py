"""Elasticsearch connector with query execution and index management."""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from src.models.database_connection import DatabaseConnection
from src.services.agents.security import decrypt_value

logger = logging.getLogger(__name__)


class ElasticsearchConnector:
    """
    Elasticsearch connector for search and analytics queries.

    Provides connection management, query execution, and index introspection
    for Elasticsearch clusters.
    """

    def __init__(self, database_connection: DatabaseConnection, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Elasticsearch connector.

        Args:
            database_connection: DatabaseConnection model instance
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.database_connection = database_connection
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: AsyncElasticsearch | None = None

    async def connect(self) -> bool:
        """
        Establish connection to Elasticsearch.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Decrypt password if present
            password = None
            if self.database_connection.password_encrypted:
                password = decrypt_value(self.database_connection.password_encrypted)

            # Get connection parameters
            conn_params = self.database_connection.connection_params or {}
            # Default to HTTP (use_ssl=False) for development ease
            # Set use_ssl=True in connection_params for production
            use_ssl = conn_params.get("use_ssl", False)
            verify_certs = conn_params.get("verify_certs", False)

            # Build connection URL
            scheme = "https" if use_ssl else "http"
            url = f"{scheme}://{self.database_connection.host}:{self.database_connection.port}"

            # Create client with or without authentication
            client_kwargs = {
                "hosts": [url],
                "verify_certs": verify_certs,
                "request_timeout": self.timeout,
                "max_retries": self.max_retries,
                "retry_on_timeout": True,
            }

            # Only add basic_auth if username and password are provided
            if self.database_connection.username and password:
                client_kwargs["basic_auth"] = (self.database_connection.username, password)

            self.client = AsyncElasticsearch(**client_kwargs)

            # Test connection
            await self.client.info()

            logger.info(f"Connected to Elasticsearch: {self.database_connection.host}:{self.database_connection.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Close the connection to Elasticsearch."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Elasticsearch")

    async def test_connection(self) -> dict[str, Any]:
        """
        Test the connection to Elasticsearch.

        Returns:
            Dictionary with test results
        """
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to establish connection", "details": {}}

            # Get cluster info
            info = await self.client.info()
            health = await self.client.cluster.health()

            await self.disconnect()

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "cluster_name": info.get("cluster_name"),
                    "version": info.get("version", {}).get("number"),
                    "status": health.get("status"),
                    "number_of_nodes": health.get("number_of_nodes"),
                    "number_of_data_nodes": health.get("number_of_data_nodes"),
                },
            }

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}", "details": {}}

    async def execute_search(
        self, index: str, query: dict[str, Any], size: int = 100, from_: int = 0
    ) -> dict[str, Any]:
        """
        Execute a search query.

        Args:
            index: Index name or pattern
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Starting offset

        Returns:
            Dictionary with search results
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            response = await self.client.search(index=index, body=query, size=size, from_=from_)

            # Extract hits
            hits = response.get("hits", {})
            total = hits.get("total", {})
            documents = hits.get("hits", [])

            # Format results
            results = []
            for doc in documents:
                results.append(
                    {
                        "_index": doc.get("_index"),
                        "_id": doc.get("_id"),
                        "_score": doc.get("_score"),
                        "_source": doc.get("_source", {}),
                    }
                )

            return {
                "success": True,
                "total": total.get("value", 0),
                "results": results,
                "took": response.get("took"),
                "aggregations": response.get("aggregations", {}),
            }

        except Exception as e:
            logger.error(f"Search query failed: {str(e)}")
            return {"success": False, "total": 0, "results": [], "error": str(e)}

    async def execute_count(self, index: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a count query.

        Args:
            index: Index name or pattern
            query: Elasticsearch query DSL (optional)

        Returns:
            Dictionary with count result
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            body = {"query": query} if query else None
            response = await self.client.count(index=index, body=body)

            return {"success": True, "count": response.get("count", 0)}

        except Exception as e:
            logger.error(f"Count query failed: {str(e)}")
            return {"success": False, "count": 0, "error": str(e)}

    async def get_indices(self) -> dict[str, Any]:
        """
        Get list of all indices.

        Returns:
            Dictionary with indices information
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            # Get all indices
            indices = await self.client.cat.indices(format="json")

            # Format results
            result = []
            for index in indices:
                result.append(
                    {
                        "name": index.get("index"),
                        "health": index.get("health"),
                        "status": index.get("status"),
                        "docs_count": int(index.get("docs.count", 0)),
                        "store_size": index.get("store.size"),
                    }
                )

            return {"success": True, "indices": result}

        except Exception as e:
            logger.error(f"Failed to get indices: {str(e)}")
            return {"success": False, "indices": [], "error": str(e)}

    async def get_index_mapping(self, index: str) -> dict[str, Any]:
        """
        Get mapping for a specific index.

        Args:
            index: Index name

        Returns:
            Dictionary with mapping information
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            mapping = await self.client.indices.get_mapping(index=index)

            # Extract fields from mapping
            index_mapping = mapping.get(index, {})
            mappings = index_mapping.get("mappings", {})
            properties = mappings.get("properties", {})

            # Format fields
            fields = []
            for field_name, field_info in properties.items():
                fields.append(
                    {"name": field_name, "type": field_info.get("type"), "properties": field_info.get("properties", {})}
                )

            return {"success": True, "index": index, "fields": fields, "mapping": mappings}

        except NotFoundError:
            return {"success": False, "error": f"Index '{index}' not found"}
        except Exception as e:
            logger.error(f"Failed to get index mapping: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_index_settings(self, index: str) -> dict[str, Any]:
        """
        Get settings for a specific index.

        Args:
            index: Index name

        Returns:
            Dictionary with settings information
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            settings = await self.client.indices.get_settings(index=index)

            index_settings = settings.get(index, {})

            return {"success": True, "index": index, "settings": index_settings.get("settings", {})}

        except NotFoundError:
            return {"success": False, "error": f"Index '{index}' not found"}
        except Exception as e:
            logger.error(f"Failed to get index settings: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_sample_documents(self, index: str, size: int = 10) -> dict[str, Any]:
        """
        Get sample documents from an index.

        Args:
            index: Index name
            size: Number of documents to fetch

        Returns:
            Dictionary with sample documents
        """
        try:
            query = {"query": {"match_all": {}}}
            result = await self.execute_search(index, query, size=size)
            return result

        except Exception as e:
            logger.error(f"Failed to get sample documents: {str(e)}")
            return {"success": False, "results": [], "error": str(e)}

    async def execute_aggregation(
        self, index: str, aggregations: dict[str, Any], query: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute an aggregation query.

        Args:
            index: Index name or pattern
            aggregations: Aggregation definition
            query: Optional query to filter documents

        Returns:
            Dictionary with aggregation results
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            body = {"size": 0, "aggs": aggregations}

            if query:
                body["query"] = query

            response = await self.client.search(index=index, body=body)

            return {"success": True, "aggregations": response.get("aggregations", {}), "took": response.get("took")}

        except Exception as e:
            logger.error(f"Aggregation query failed: {str(e)}")
            return {"success": False, "aggregations": {}, "error": str(e)}
