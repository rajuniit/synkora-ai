"""Docker logs connector for data analysis."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class DockerLogsConnector(BaseConnector):
    """Connector for Docker container logs."""

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """Initialize Docker logs connector.

        Args:
            data_source: DataSource model instance
            db: Database session
        """
        super().__init__(data_source, db)
        self.docker_host = self.config.get("host", "unix:///var/run/docker.sock")
        self.container_ids = self.config.get("container_ids", [])
        self.container_names = self.config.get("container_names", [])

    async def test_connection(self) -> dict[str, Any]:
        """Test connection to Docker daemon.

        Returns:
            Dict with success status and message
        """
        try:
            # Test connection using Docker SDK
            try:
                import docker
            except ImportError:
                return {
                    "success": False,
                    "message": "docker package not installed. Install with: pip install docker",
                    "details": {},
                }

            client = docker.DockerClient(base_url=self.docker_host)

            # Test connection by getting Docker version
            version_info = client.version()

            # List containers
            containers = client.containers.list(all=True)

            client.close()

            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "docker_version": version_info.get("Version"),
                    "api_version": version_info.get("ApiVersion"),
                    "containers_count": len(containers),
                },
            }

        except Exception as e:
            logger.error(f"Docker connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {str(e)}", "details": {"error": str(e)}}

    async def list_containers(self, all_containers: bool = True) -> dict[str, Any]:
        """List Docker containers.

        Args:
            all_containers: Include stopped containers

        Returns:
            Dict with container list
        """
        try:
            import docker

            client = docker.DockerClient(base_url=self.docker_host)
            containers = client.containers.list(all=all_containers)

            container_list = []
            for container in containers:
                container_list.append(
                    {
                        "id": container.id,
                        "short_id": container.short_id,
                        "name": container.name,
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else str(container.image.id),
                        "created": container.attrs.get("Created"),
                        "labels": container.labels,
                    }
                )

            client.close()

            return {"success": True, "containers": container_list, "count": len(container_list)}

        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return {"success": False, "message": f"Failed to list containers: {str(e)}", "error": str(e)}

    async def fetch_logs(
        self,
        container_id: str | None = None,
        container_name: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        tail: int = 1000,
        timestamps: bool = True,
    ) -> dict[str, Any]:
        """Fetch logs from Docker container.

        Args:
            container_id: Container ID
            container_name: Container name
            since: Fetch logs since this datetime
            until: Fetch logs until this datetime
            tail: Number of lines to return from the end
            timestamps: Include timestamps

        Returns:
            Dict with container logs
        """
        try:
            import docker

            if not container_id and not container_name:
                return {
                    "success": False,
                    "message": "Either container_id or container_name must be provided",
                    "error": "Missing container identifier",
                }

            client = docker.DockerClient(base_url=self.docker_host)

            # Get container
            if container_id:
                container = client.containers.get(container_id)
            else:
                containers = client.containers.list(all=True, filters={"name": container_name})
                if not containers:
                    return {
                        "success": False,
                        "message": f"Container '{container_name}' not found",
                        "error": "Container not found",
                    }
                container = containers[0]

            # Fetch logs
            log_kwargs = {"timestamps": timestamps, "tail": tail}

            if since:
                log_kwargs["since"] = since
            if until:
                log_kwargs["until"] = until

            logs = container.logs(**log_kwargs).decode("utf-8")

            # Parse logs into structured format
            log_lines = []
            for line in logs.strip().split("\n"):
                if timestamps and line:
                    # Parse timestamp if present
                    try:
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            log_lines.append({"timestamp": parts[0], "message": parts[1]})
                        else:
                            log_lines.append({"timestamp": None, "message": line})
                    except:
                        log_lines.append({"timestamp": None, "message": line})
                else:
                    log_lines.append({"timestamp": None, "message": line})

            client.close()

            return {
                "success": True,
                "container": {"id": container.id, "name": container.name, "status": container.status},
                "logs": log_lines,
                "count": len(log_lines),
            }

        except Exception as e:
            logger.error(f"Failed to fetch Docker logs: {e}")
            return {"success": False, "message": f"Failed to fetch logs: {str(e)}", "error": str(e)}

    async def fetch_all_configured_logs(self, since: datetime | None = None, tail: int = 1000) -> dict[str, Any]:
        """Fetch logs from all configured containers.

        Args:
            since: Fetch logs since this datetime
            tail: Number of lines per container

        Returns:
            Dict with logs from all containers
        """
        try:
            all_logs = []
            errors = []

            # Fetch logs from containers by ID
            for container_id in self.container_ids:
                result = await self.fetch_logs(container_id=container_id, since=since, tail=tail)
                if result["success"]:
                    all_logs.append(result)
                else:
                    errors.append({"container_id": container_id, "error": result.get("message")})

            # Fetch logs from containers by name
            for container_name in self.container_names:
                result = await self.fetch_logs(container_name=container_name, since=since, tail=tail)
                if result["success"]:
                    all_logs.append(result)
                else:
                    errors.append({"container_name": container_name, "error": result.get("message")})

            return {
                "success": True,
                "containers": all_logs,
                "errors": errors,
                "total_containers": len(all_logs),
                "failed_containers": len(errors),
            }

        except Exception as e:
            logger.error(f"Failed to fetch all Docker logs: {e}")
            return {"success": False, "message": f"Failed to fetch logs: {str(e)}", "error": str(e)}

    async def sync(self, incremental: bool = True) -> dict[str, Any]:
        """Sync data from Docker logs (not typically used for analysis).

        Args:
            incremental: Whether to do incremental sync

        Returns:
            Dict with sync results
        """
        # For analysis purposes, we don't typically sync Docker logs
        # Instead, we query on-demand
        return {
            "success": True,
            "message": "Docker logs connector is query-based, no sync needed",
            "documents_processed": 0,
            "documents_added": 0,
            "documents_updated": 0,
            "documents_failed": 0,
        }

    def get_oauth_url(self) -> str | None:
        """Get OAuth URL (Docker doesn't use OAuth)."""
        return None

    async def handle_oauth_callback(self, code: str) -> dict[str, Any]:
        """Handle OAuth callback (not applicable for Docker)."""
        return {"success": False, "message": "Docker doesn't use OAuth authentication"}

    async def connect(self) -> bool:
        """Establish connection to Docker."""
        result = await self.test_connection()
        return result.get("success", False)

    async def disconnect(self) -> None:
        """Close connection to Docker."""
        # No persistent connection to close
        pass

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch documents from Docker logs (not implemented - query-based connector)."""
        return []

    async def get_document_count(self) -> int:
        """Get total number of documents (not implemented - query-based connector)."""
        return 0

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return []  # Docker host is optional (defaults to local socket)
