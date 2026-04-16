"""
K6 Runner Service

A lightweight service that executes K6 load tests and streams results.
This runs inside the k6-runner container.

Features:
- Accepts test scripts via Redis pub/sub or HTTP
- Executes K6 and captures output
- Streams results back via Redis
- Supports cancellation

Environment Variables:
    REDIS_URL: Redis connection string
    SYNKORA_API_URL: Synkora API URL for callbacks
    CALLBACK_URL: URL to POST results to
    K6_SCRIPTS_DIR: Directory for test scripts
    K6_RESULTS_DIR: Directory for results
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import redis

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("k6-runner")


@dataclass
class TestJob:
    """Represents a K6 test job."""

    test_run_id: str
    k6_script: str
    callback_url: str | None = None
    options: dict | None = None


class K6RunnerService:
    """
    Service for executing K6 load tests.

    Listens for test requests on Redis and executes them.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.callback_url = os.getenv("CALLBACK_URL")
        self.scripts_dir = Path(os.getenv("K6_SCRIPTS_DIR", "/scripts"))
        self.results_dir = Path(os.getenv("K6_RESULTS_DIR", "/results"))
        self.current_process: subprocess.Popen | None = None
        self.current_job: TestJob | None = None
        self.running = True

        # Ensure directories exist
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.current_process:
            logger.info("Terminating running K6 process...")
            self.current_process.terminate()

    def connect_redis(self) -> redis.Redis:
        """Connect to Redis."""
        return redis.from_url(self.redis_url, decode_responses=True)

    async def execute_test(self, job: TestJob) -> dict[str, Any]:
        """
        Execute a K6 test.

        Args:
            job: The test job to execute

        Returns:
            dict: Test results
        """
        self.current_job = job
        start_time = time.time()
        results_file = self.results_dir / f"{job.test_run_id}.json"

        logger.info(f"Starting test run: {job.test_run_id}")

        # Write script to file
        script_file = self.scripts_dir / f"{job.test_run_id}.js"
        script_file.write_text(job.k6_script)

        try:
            # Build K6 command
            cmd = [
                "k6",
                "run",
                "--out",
                f"json={results_file}",
                "--summary-export",
                str(self.results_dir / f"{job.test_run_id}_summary.json"),
                str(script_file),
            ]

            # Add custom options
            if job.options:
                if job.options.get("vus"):
                    cmd.extend(["--vus", str(job.options["vus"])])
                if job.options.get("duration"):
                    cmd.extend(["--duration", job.options["duration"]])

            logger.info(f"Executing: {' '.join(cmd)}")

            # Start K6 process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream output
            redis_client = self.connect_redis()
            output_lines = []

            for line in self.current_process.stdout:
                line = line.strip()
                if line:
                    output_lines.append(line)
                    logger.debug(f"K6: {line}")

                    # Publish to Redis for real-time monitoring
                    try:
                        redis_client.publish(
                            f"k6:output:{job.test_run_id}",
                            json.dumps({"line": line, "timestamp": datetime.now(UTC).isoformat()}),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to publish to Redis: {e}")

            # Wait for completion
            return_code = self.current_process.wait()

            duration = time.time() - start_time
            success = return_code == 0

            logger.info(f"Test completed: {job.test_run_id} (success={success}, duration={duration:.2f}s)")

            # Read summary
            summary = {}
            summary_file = self.results_dir / f"{job.test_run_id}_summary.json"
            if summary_file.exists():
                try:
                    summary = json.loads(summary_file.read_text())
                except Exception as e:
                    logger.error(f"Failed to read summary: {e}")

            result = {
                "test_run_id": job.test_run_id,
                "success": success,
                "return_code": return_code,
                "duration_seconds": duration,
                "summary": summary,
                "output_lines": output_lines[-100:],  # Last 100 lines
            }

            # Send callback
            if job.callback_url or self.callback_url:
                await self._send_callback(job.callback_url or self.callback_url, result)

            # Publish completion
            redis_client.publish(f"k6:complete:{job.test_run_id}", json.dumps(result))

            return result

        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            return {
                "test_run_id": job.test_run_id,
                "success": False,
                "error": str(e),
                "duration_seconds": time.time() - start_time,
            }

        finally:
            self.current_process = None
            self.current_job = None

            # Cleanup script file
            try:
                script_file.unlink(missing_ok=True)
            except Exception:
                pass

    async def _send_callback(self, url: str, result: dict):
        """Send results to callback URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=result)
                response.raise_for_status()
                logger.info(f"Callback sent successfully to {url}")
        except Exception as e:
            logger.error(f"Failed to send callback: {e}")

    async def cancel_test(self, test_run_id: str):
        """Cancel a running test."""
        if self.current_job and self.current_job.test_run_id == test_run_id:
            if self.current_process:
                logger.info(f"Cancelling test: {test_run_id}")
                self.current_process.terminate()
                return True
        return False

    async def listen_for_jobs(self):
        """Listen for test jobs on Redis pub/sub."""
        redis_client = self.connect_redis()
        pubsub = redis_client.pubsub()
        pubsub.subscribe("k6:jobs", "k6:cancel")

        logger.info("Listening for K6 test jobs...")

        while self.running:
            try:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    if channel == "k6:jobs":
                        job = TestJob(
                            test_run_id=data["test_run_id"],
                            k6_script=data["k6_script"],
                            callback_url=data.get("callback_url"),
                            options=data.get("options"),
                        )
                        await self.execute_test(job)

                    elif channel == "k6:cancel":
                        await self.cancel_test(data["test_run_id"])

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)

    def run(self):
        """Run the K6 runner service."""
        logger.info("=" * 60)
        logger.info("K6 Runner Service Starting")
        logger.info("=" * 60)
        logger.info(f"Redis URL: {self.redis_url}")
        logger.info(f"Callback URL: {self.callback_url}")
        logger.info(f"Scripts Dir: {self.scripts_dir}")
        logger.info(f"Results Dir: {self.results_dir}")
        logger.info("=" * 60)

        # Verify K6 is installed
        try:
            result = subprocess.run(["k6", "version"], capture_output=True, text=True)
            logger.info(f"K6 Version: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("K6 binary not found!")
            sys.exit(1)

        # Run the async event loop
        asyncio.run(self.listen_for_jobs())


if __name__ == "__main__":
    service = K6RunnerService()
    service.run()
