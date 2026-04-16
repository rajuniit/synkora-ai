"""HTTP health check server for bot workers.

Provides /healthz and /readyz endpoints for Kubernetes probes.
"""

import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from .worker import BotWorker

logger = logging.getLogger(__name__)


class HealthServer:
    """Simple HTTP server for health checks."""

    def __init__(self, worker: "BotWorker", port: int = 8080):
        """Initialize the health server.

        Args:
            worker: BotWorker instance to check health of
            port: Port to listen on
        """
        self.worker = worker
        self.port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def start(self) -> None:
        """Start the health server."""
        self._app = web.Application()
        self._app.router.add_get("/healthz", self._healthz)
        self._app.router.add_get("/readyz", self._readyz)
        self._app.router.add_get("/metrics", self._metrics)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await self._site.start()

        logger.info(f"Health server started on port {self.port}")

    async def stop(self) -> None:
        """Stop the health server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        logger.info("Health server stopped")

    async def _healthz(self, request: web.Request) -> web.Response:
        """Liveness probe endpoint.

        Returns 200 if the worker process is alive.
        """
        return web.json_response(
            {
                "status": "healthy",
                "worker_id": self.worker.worker_id,
                "uptime_seconds": self.worker.uptime_seconds,
            }
        )

    async def _readyz(self, request: web.Request) -> web.Response:
        """Readiness probe endpoint.

        Returns 200 if the worker is ready to handle bots.
        Returns 503 if the worker is shutting down or not ready.
        """
        if self.worker.is_shutting_down:
            return web.json_response(
                {"status": "shutting_down", "worker_id": self.worker.worker_id},
                status=503,
            )

        if not self.worker.is_ready:
            return web.json_response(
                {"status": "not_ready", "worker_id": self.worker.worker_id},
                status=503,
            )

        return web.json_response(
            {
                "status": "ready",
                "worker_id": self.worker.worker_id,
                "active_bots": self.worker.active_bot_count,
                "capacity": self.worker.capacity,
            }
        )

    async def _metrics(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        metrics = self._generate_prometheus_metrics()
        return web.Response(text=metrics, content_type="text/plain")

    def _generate_prometheus_metrics(self) -> str:
        """Generate Prometheus format metrics."""
        lines = []
        worker_id = self.worker.worker_id

        # Worker info
        lines.append("# HELP bot_worker_info Bot worker information")
        lines.append("# TYPE bot_worker_info gauge")
        lines.append(f'bot_worker_info{{worker_id="{worker_id}"}} 1')

        # Active bots
        lines.append("# HELP bot_worker_active_bots Number of active bots on this worker")
        lines.append("# TYPE bot_worker_active_bots gauge")
        lines.append(f'bot_worker_active_bots{{worker_id="{worker_id}"}} {self.worker.active_bot_count}')

        # Capacity
        lines.append("# HELP bot_worker_capacity Maximum bot capacity for this worker")
        lines.append("# TYPE bot_worker_capacity gauge")
        lines.append(f'bot_worker_capacity{{worker_id="{worker_id}"}} {self.worker.capacity}')

        # Uptime
        lines.append("# HELP bot_worker_uptime_seconds Worker uptime in seconds")
        lines.append("# TYPE bot_worker_uptime_seconds counter")
        lines.append(f'bot_worker_uptime_seconds{{worker_id="{worker_id}"}} {self.worker.uptime_seconds:.2f}')

        # Bot counts by type
        slack_count = len([b for b in self.worker._active_bots.values() if b.get("type") == "slack"])
        telegram_count = len([b for b in self.worker._active_bots.values() if b.get("type") == "telegram"])

        lines.append("# HELP bot_worker_bots_by_type Number of bots by type")
        lines.append("# TYPE bot_worker_bots_by_type gauge")
        lines.append(f'bot_worker_bots_by_type{{worker_id="{worker_id}",type="slack"}} {slack_count}')
        lines.append(f'bot_worker_bots_by_type{{worker_id="{worker_id}",type="telegram"}} {telegram_count}')

        return "\n".join(lines) + "\n"
