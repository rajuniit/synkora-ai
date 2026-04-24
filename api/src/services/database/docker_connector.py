"""Docker connector for container logs and status queries."""

import logging
from typing import Any

from src.models.database_connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DockerConnector:
    """
    Docker connector for querying container state and logs.

    Connection fields (re-uses existing DatabaseConnection columns):
      host -> Docker base URL (e.g. unix://var/run/docker.sock or tcp://host:2375)
    """

    def __init__(self, database_connection: DatabaseConnection):
        self.database_connection = database_connection

    def _base_url(self) -> str:
        return self.database_connection.host or "unix://var/run/docker.sock"

    async def test_connection(self) -> dict[str, Any]:
        """Test connection by pinging the Docker daemon."""
        import asyncio

        base_url = self._base_url()
        if not base_url:
            return {"success": False, "message": "Docker host is required"}

        def _sync_ping():
            import docker

            client = docker.DockerClient(base_url=base_url, timeout=10)
            try:
                client.ping()
                version = client.version()
                return version.get("Version", "unknown")
            finally:
                client.close()

        try:
            version = await asyncio.get_event_loop().run_in_executor(None, _sync_ping)
            return {
                "success": True,
                "message": f"Connected to Docker daemon ({base_url})",
                "details": {"base_url": base_url, "docker_version": version},
            }
        except Exception as e:
            logger.error(f"Docker connection test failed: {e}")
            return {"success": False, "message": f"Connection failed: {e}"}

    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a pseudo-query against Docker.

        Supported query keywords:
          - 'containers' / 'ps'      -> list containers
          - 'images'                 -> list images
          - 'logs <container_id>'    -> fetch last 100 log lines
          - 'inspect <container_id>' -> inspect a container
        """
        import asyncio

        base_url = self._base_url()
        q = query.strip().lower()

        def _sync_exec():
            import docker

            client = docker.DockerClient(base_url=base_url, timeout=30)
            try:
                if q in ("containers", "ps"):
                    containers = client.containers.list(all=True)
                    return [
                        {
                            "id": c.short_id,
                            "name": c.name,
                            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                            "status": c.status,
                            "created": str(c.attrs.get("Created", "")),
                        }
                        for c in containers
                    ]
                elif q == "images":
                    images = client.images.list()
                    return [
                        {
                            "id": img.short_id,
                            "tags": img.tags,
                            "size": img.attrs.get("Size", 0),
                        }
                        for img in images
                    ]
                elif q.startswith("logs "):
                    container_id = query.split(" ", 1)[1].strip()
                    container = client.containers.get(container_id)
                    logs = container.logs(tail=100, timestamps=True).decode("utf-8", errors="replace")
                    return {"container_id": container_id, "logs": logs}
                elif q.startswith("inspect "):
                    container_id = query.split(" ", 1)[1].strip()
                    container = client.containers.get(container_id)
                    return container.attrs
                else:
                    return {
                        "error": f"Unknown query: '{query}'. Supported: containers, images, logs <id>, inspect <id>"
                    }
            finally:
                client.close()

        try:
            data = await asyncio.get_event_loop().run_in_executor(None, _sync_exec)
            return {"success": True, "data": data}
        except Exception as e:
            logger.error(f"Docker query failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_schema(self) -> dict[str, Any]:
        """List running containers as a pseudo-schema."""
        return await self.execute_query("containers")
