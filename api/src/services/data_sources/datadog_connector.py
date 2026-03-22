"""Datadog connector for data analysis."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class DatadogConnector(BaseConnector):
    """Connector for Datadog metrics and logs."""

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """Initialize Datadog connector.

        Args:
            data_source: DataSource model instance
            db: Database session
        """
        super().__init__(data_source, db)
        self.api_key = self.config.get("api_key")
        self.app_key = self.config.get("app_key")
        self.site = self.config.get("site", "datadoghq.com")
        self.base_url = f"https://api.{self.site}"

    async def test_connection(self) -> dict[str, Any]:
        """Test connection to Datadog API.

        Returns:
            Dict with success status and message
        """
        try:
            if not self.api_key or not self.app_key:
                return {"success": False, "message": "API key and App key are required", "details": {}}

            # Test connection by validating API keys
            import httpx

            headers = {"DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/validate", headers=headers, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("valid", False),
                    "message": "Connection successful" if data.get("valid") else "Invalid credentials",
                    "details": {"site": self.site},
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {response.status_code}",
                    "details": {"status_code": response.status_code},
                }

        except Exception as e:
            logger.error(f"Datadog connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {str(e)}", "details": {"error": str(e)}}

    async def fetch_metrics(
        self, query: str, from_time: datetime | None = None, to_time: datetime | None = None
    ) -> dict[str, Any]:
        """Fetch metrics from Datadog.

        Args:
            query: Datadog metrics query
            from_time: Start time for query (default: 1 hour ago)
            to_time: End time for query (default: now)

        Returns:
            Dict with metrics data
        """
        try:
            import httpx

            if not from_time:
                from_time = datetime.now(UTC) - timedelta(hours=1)
            if not to_time:
                to_time = datetime.now(UTC)

            headers = {"DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key}

            params = {"query": query, "from": int(from_time.timestamp()), "to": int(to_time.timestamp())}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query", headers=headers, params=params, timeout=30.0
                )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "query": query,
                    "time_range": {"from": from_time.isoformat(), "to": to_time.isoformat()},
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to fetch metrics: HTTP {response.status_code}",
                    "error": response.text,
                }

        except Exception as e:
            logger.error(f"Failed to fetch Datadog metrics: {e}")
            return {"success": False, "message": f"Failed to fetch metrics: {str(e)}", "error": str(e)}

    async def fetch_logs(
        self, query: str, from_time: datetime | None = None, to_time: datetime | None = None, limit: int = 1000
    ) -> dict[str, Any]:
        """Fetch logs from Datadog.

        Args:
            query: Datadog logs query
            from_time: Start time for query (default: 1 hour ago)
            to_time: End time for query (default: now)
            limit: Maximum number of logs to fetch

        Returns:
            Dict with logs data
        """
        try:
            import httpx

            if not from_time:
                from_time = datetime.now(UTC) - timedelta(hours=1)
            if not to_time:
                to_time = datetime.now(UTC)

            headers = {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json",
            }

            body = {
                "filter": {"query": query, "from": from_time.isoformat(), "to": to_time.isoformat()},
                "page": {"limit": limit},
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v2/logs/events/search", headers=headers, json=body, timeout=30.0
                )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "query": query,
                    "count": len(data.get("data", [])),
                    "time_range": {"from": from_time.isoformat(), "to": to_time.isoformat()},
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to fetch logs: HTTP {response.status_code}",
                    "error": response.text,
                }

        except Exception as e:
            logger.error(f"Failed to fetch Datadog logs: {e}")
            return {"success": False, "message": f"Failed to fetch logs: {str(e)}", "error": str(e)}

    async def sync(self, incremental: bool = True) -> dict[str, Any]:
        """Sync data from Datadog (not typically used for analysis).

        Args:
            incremental: Whether to do incremental sync

        Returns:
            Dict with sync results
        """
        # For analysis purposes, we don't typically sync Datadog data
        # Instead, we query on-demand
        return {
            "success": True,
            "message": "Datadog connector is query-based, no sync needed",
            "documents_processed": 0,
            "documents_added": 0,
            "documents_updated": 0,
            "documents_failed": 0,
        }

    def get_oauth_url(self) -> str | None:
        """Get OAuth URL (Datadog uses API keys, not OAuth)."""
        return None

    async def handle_oauth_callback(self, code: str) -> dict[str, Any]:
        """Handle OAuth callback (not applicable for Datadog)."""
        return {"success": False, "message": "Datadog uses API keys, not OAuth"}

    async def connect(self) -> bool:
        """Establish connection to Datadog."""
        result = await self.test_connection()
        return result.get("success", False)

    async def disconnect(self) -> None:
        """Close connection to Datadog."""
        # No persistent connection to close
        pass

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch documents from Datadog (not implemented - query-based connector)."""
        return []

    async def get_document_count(self) -> int:
        """Get total number of documents (not implemented - query-based connector)."""
        return 0

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return ["api_key", "app_key"]
