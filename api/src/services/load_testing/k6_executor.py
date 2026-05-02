"""
K6 Executor

Executes K6 load tests using Docker or Kubernetes.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class K6ExecutorError(Exception):
    """Error during K6 execution."""

    pass


class K6Executor:
    """
    Executes K6 load tests and streams results.

    Supports execution via:
    - Local K6 binary
    - Docker container
    - Kubernetes job (future)
    """

    def __init__(
        self,
        test_run_id: UUID,
        k6_script: str,
        callback_url: str | None = None,
        docker_image: str = "grafana/k6:latest",
    ):
        """
        Initialize the executor.

        Args:
            test_run_id: The test run ID
            k6_script: The K6 JavaScript code
            callback_url: Optional URL for results callback
            docker_image: Docker image to use
        """
        self.test_run_id = test_run_id
        self.k6_script = k6_script
        self.callback_url = callback_url
        self.docker_image = docker_image
        self._process: subprocess.Popen | None = None
        self._container_id: str | None = None
        self._cancelled = False

    async def execute_local(
        self,
        on_metrics: Callable[[dict], None] | None = None,
    ) -> dict:
        """
        Execute K6 using local binary.

        Args:
            on_metrics: Callback for streaming metrics

        Returns:
            dict: Summary results
        """
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(self.k6_script)
            script_path = f.name

        try:
            # Build K6 command
            cmd = [
                "k6",
                "run",
                "--out",
                "json=-",  # Output JSON to stdout
                script_path,
            ]

            logger.info(f"Executing K6 command: {' '.join(cmd)}")

            # Run K6 process
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            results = {"metrics": [], "summary": None, "error": None}

            # Read output
            async for line in self._process.stdout:
                if self._cancelled:
                    break

                line = line.decode().strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    metric_type = data.get("type")

                    if metric_type == "Metric":
                        # Streaming metric
                        metric = {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "metric": data.get("metric"),
                            "data": data.get("data"),
                        }
                        results["metrics"].append(metric)

                        if on_metrics:
                            on_metrics(metric)

                    elif metric_type == "Point":
                        # Data point
                        point = {
                            "timestamp": data.get("data", {}).get("time"),
                            "metric": data.get("metric"),
                            "value": data.get("data", {}).get("value"),
                            "tags": data.get("data", {}).get("tags"),
                        }

                        if on_metrics:
                            on_metrics(point)

                except json.JSONDecodeError:
                    # Might be summary or logs
                    if line.startswith("{"):
                        try:
                            results["summary"] = json.loads(line)
                        except Exception:
                            pass

            # Wait for completion
            await self._process.wait()

            # Check for errors
            if self._process.returncode != 0 and not self._cancelled:
                stderr = await self._process.stderr.read()
                error_msg = stderr.decode() if stderr else "Unknown error"
                results["error"] = error_msg
                logger.error(f"K6 execution failed: {error_msg}")

            return results

        finally:
            # Cleanup
            try:
                os.unlink(script_path)
            except Exception:
                pass

    async def execute_docker(
        self,
        on_metrics: Callable[[dict], None] | None = None,
    ) -> dict:
        """
        Execute K6 using Docker container.

        Args:
            on_metrics: Callback for streaming metrics

        Returns:
            dict: Summary results
        """
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(self.k6_script)
            script_path = f.name

        try:
            script_dir = os.path.dirname(script_path)
            script_name = os.path.basename(script_path)

            # Build Docker command
            cmd = [
                "docker",
                "run",
                "--rm",
                "--name",
                f"k6-{self.test_run_id}",
                "-v",
                f"{script_dir}:/scripts",
                "--network",
                # host network lets k6 reach localhost services.
                # SECURITY: user-supplied k6 scripts can probe any host-reachable address.
                # For multi-tenant SaaS deployments, replace with an isolated bridge network.
                "host",
                self.docker_image,
                "run",
                "--out",
                "json=/dev/stdout",
                f"/scripts/{script_name}",
            ]

            logger.info(f"Executing K6 in Docker: {' '.join(cmd)}")

            # Run Docker process
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._container_id = f"k6-{self.test_run_id}"
            results = {"metrics": [], "summary": None, "error": None}

            # Read output
            async for line in self._process.stdout:
                if self._cancelled:
                    break

                line = line.decode().strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    metric_type = data.get("type")

                    if metric_type == "Point":
                        point = {
                            "timestamp": data.get("data", {}).get("time"),
                            "metric": data.get("metric"),
                            "value": data.get("data", {}).get("value"),
                            "tags": data.get("data", {}).get("tags"),
                        }

                        if on_metrics:
                            on_metrics(point)

                except json.JSONDecodeError:
                    if line.startswith("{"):
                        try:
                            results["summary"] = json.loads(line)
                        except Exception:
                            pass

            # Wait for completion
            await self._process.wait()

            if self._process.returncode != 0 and not self._cancelled:
                stderr = await self._process.stderr.read()
                error_msg = stderr.decode() if stderr else "Unknown error"
                results["error"] = error_msg
                logger.error(f"K6 Docker execution failed: {error_msg}")

            return results

        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    async def cancel(self) -> None:
        """Cancel the running test."""
        self._cancelled = True

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except TimeoutError:
                self._process.kill()

        if self._container_id:
            try:
                subprocess.run(
                    ["docker", "stop", self._container_id],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass

        logger.info(f"Test run {self.test_run_id} cancelled")

    def parse_summary(self, summary_data: dict) -> dict:
        """
        Parse K6 summary into standard metrics format.

        Args:
            summary_data: Raw K6 summary output

        Returns:
            dict: Parsed metrics
        """
        metrics = summary_data.get("metrics", {})

        def get_metric_value(metric_name: str, stat: str = "avg") -> float | None:
            metric = metrics.get(metric_name, {})
            values = metric.get("values", {})
            return values.get(stat)

        return {
            "http_req_duration_p50": get_metric_value("http_req_duration", "med"),
            "http_req_duration_p95": get_metric_value("http_req_duration", "p(95)"),
            "http_req_duration_p99": get_metric_value("http_req_duration", "p(99)"),
            "http_req_duration_avg": get_metric_value("http_req_duration", "avg"),
            "http_req_duration_min": get_metric_value("http_req_duration", "min"),
            "http_req_duration_max": get_metric_value("http_req_duration", "max"),
            "http_reqs": get_metric_value("http_reqs", "count"),
            "http_reqs_per_sec": get_metric_value("http_reqs", "rate"),
            "http_req_failed": get_metric_value("http_req_failed", "rate"),
            "vus_max": get_metric_value("vus_max", "max"),
            "data_received": get_metric_value("data_received", "count"),
            "data_sent": get_metric_value("data_sent", "count"),
            "iterations": get_metric_value("iterations", "count"),
            "ttft_p50": get_metric_value("ttft", "med"),
            "ttft_p95": get_metric_value("ttft", "p(95)"),
            "tokens_per_sec_avg": get_metric_value("tokens_per_sec", "avg"),
        }


class K6ExecutorFactory:
    """Factory for creating K6 executors."""

    @staticmethod
    def create(
        test_run_id: UUID,
        k6_script: str,
        execution_mode: str = "docker",
        **kwargs,
    ) -> K6Executor:
        """
        Create an executor for the specified mode.

        Args:
            test_run_id: The test run ID
            k6_script: The K6 script
            execution_mode: "local", "docker", or "kubernetes"
            **kwargs: Additional executor arguments

        Returns:
            K6Executor: The executor instance
        """
        return K6Executor(
            test_run_id=test_run_id,
            k6_script=k6_script,
            **kwargs,
        )
