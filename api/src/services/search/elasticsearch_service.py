"""
Elasticsearch Service for Synkora.

Provides Elasticsearch connection and search capabilities for agents.
"""

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import AuthenticationException, ConnectionError

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch operations."""

    def __init__(self, connection_config: dict[str, Any]):
        """
        Initialize Elasticsearch client from database connection config.

        Args:
            connection_config: Database connection configuration including:
                - host: Elasticsearch host
                - port: Elasticsearch port
                - username: Username (optional)
                - password: Password (optional)
                - connection_params: Additional parameters (api_key, use_ssl, etc.)
        """
        self.host = connection_config.get("host")
        self.port = connection_config.get("port", 9200)
        self.username = connection_config.get("username")
        self.password = connection_config.get("password")

        # Get additional params
        params = connection_config.get("connection_params", {})
        self.api_key = params.get("api_key")
        self.use_ssl = params.get("use_ssl", False)
        self.verify_certs = params.get("verify_certs", True)

        # Build connection URL
        protocol = "https" if self.use_ssl else "http"
        url = f"{protocol}://{self.host}:{self.port}"

        # Initialize client with appropriate authentication
        try:
            if self.api_key:
                self.client = AsyncElasticsearch([url], api_key=self.api_key, verify_certs=self.verify_certs)
            elif self.username and self.password:
                self.client = AsyncElasticsearch(
                    [url], basic_auth=(self.username, self.password), verify_certs=self.verify_certs
                )
            else:
                self.client = AsyncElasticsearch([url], verify_certs=self.verify_certs)
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")
            raise

    async def search(
        self, index_pattern: str, query: str, filters: dict[str, Any] | None = None, size: int = 10, from_: int = 0
    ) -> dict[str, Any]:
        """
        Generic search method that agents can use.

        Args:
            index_pattern: Index or pattern to search (e.g., "slack_messages_*")
            query: Search query string
            filters: Additional filters (date_range, term_filters, etc.)
            size: Number of results to return
            from_: Offset for pagination

        Returns:
            Dictionary with:
            - success: bool
            - total: int (total matching documents)
            - results: List of search results
            - took_ms: int (query execution time)
            - error: str (if failed)
        """
        try:
            # Build Elasticsearch query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["*"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ]
                    }
                },
                "size": min(size, 100),  # Cap at 100 for safety
                "from": from_,
                "sort": [{"_score": {"order": "desc"}}],
            }

            # Add filters if provided
            if filters:
                filter_clauses = []

                # Date range filter
                if "date_range" in filters:
                    date_filter = filters["date_range"]
                    range_query = {"range": {date_filter["field"]: {}}}
                    if "gte" in date_filter:
                        range_query["range"][date_filter["field"]]["gte"] = date_filter["gte"]
                    if "lte" in date_filter:
                        range_query["range"][date_filter["field"]]["lte"] = date_filter["lte"]
                    filter_clauses.append(range_query)

                # Term filters (exact matches)
                if "term_filters" in filters:
                    for field, value in filters["term_filters"].items():
                        filter_clauses.append({"term": {field: value}})

                if filter_clauses:
                    search_body["query"]["bool"]["filter"] = filter_clauses

            # Execute search
            response = await self.client.search(index=index_pattern, body=search_body)

            # Format results
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]
            total_value = total["value"] if isinstance(total, dict) else total

            return {
                "success": True,
                "total": total_value,
                "results": [
                    {"index": hit["_index"], "id": hit["_id"], "score": hit["_score"], "source": hit["_source"]}
                    for hit in hits
                ],
                "took_ms": response["took"],
            }

        except ConnectionError as e:
            logger.error(f"Elasticsearch connection error: {e}")
            return {"success": False, "error": f"Connection error: {str(e)}", "results": []}
        except AuthenticationException as e:
            logger.error(f"Elasticsearch authentication error: {e}")
            return {"success": False, "error": f"Authentication failed: {str(e)}", "results": []}
        except Exception as e:
            logger.error(f"Elasticsearch search error: {e}")
            return {"success": False, "error": str(e), "results": []}

    async def get_indices(self) -> list[str]:
        """Get list of available indices."""
        try:
            indices = await self.client.indices.get_alias(index="*")
            return sorted(indices.keys())
        except Exception as e:
            logger.error(f"Error getting indices: {e}")
            return []

    async def get_index_stats(self, index_pattern: str) -> dict[str, Any]:
        """Get statistics for an index or pattern."""
        try:
            stats = await self.client.indices.stats(index=index_pattern)
            all_stats = stats.get("_all", {}).get("total", {})

            return {
                "success": True,
                "document_count": all_stats.get("docs", {}).get("count", 0),
                "size_bytes": all_stats.get("store", {}).get("size_in_bytes", 0),
                "indices": list(stats.get("indices", {}).keys()),
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> dict[str, Any]:
        """Test if connection is working."""
        try:
            info = await self.client.info()
            return {
                "success": True,
                "message": f"Connected to Elasticsearch {info['version']['number']}",
                "cluster_name": info.get("cluster_name"),
                "version": info["version"]["number"],
            }
        except ConnectionError as e:
            logger.error(f"Connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {str(e)}"}
        except AuthenticationException as e:
            logger.error(f"Authentication failed: {e}")
            return {"success": False, "message": f"Authentication failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    async def close(self):
        """Close the client connection."""
        try:
            await self.client.close()
        except Exception as e:
            logger.error(f"Error closing Elasticsearch client: {e}")
