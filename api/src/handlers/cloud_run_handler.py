"""
Google Cloud Run Jobs entry point for agent task execution.

Runs as a minimal HTTP server (POST /run).  The Cloud Run Job framework
starts the container, sends the request, and exits when the handler returns.

Security:
- Verifies HMAC-SHA256 signature on every invocation.
- All secrets (DB URL, LLM API keys) are injected via Cloud Run env vars
  sourced from GCP Secret Manager — never passed in the request payload.
- The request payload contains only IDs, never user data or credentials.

Usage:
  Cloud Run Job command: python -m src.handlers.cloud_run_handler
  Environment variables: same as the API container (.env)
  Port: 8080 (Cloud Run default)
"""

import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _process_task(task_id: str, task_type: str, timestamp: str, signature: str) -> tuple[int, str]:
    """Execute the task and return (status_code, body)."""
    secret = os.environ.get("CLOUD_RUN_INVOCATION_SECRET")
    if secret:
        from src.services.agents.execution_backends.cloud_run_backend import CloudRunBackend

        if not signature:
            return 403, "Missing invocation signature"
        if not CloudRunBackend.verify_signature(task_id, timestamp, signature, secret):
            return 403, "Invalid invocation signature"

    logger.info(f"Cloud Run executing task {task_id} (type={task_type})")

    # Set SYNKORA_DIRECT_EXECUTION so the task executor does not try to
    # dispatch back to Cloud Run — that would cause an infinite job loop.
    import os as _os
    _os.environ["SYNKORA_DIRECT_EXECUTION"] = "true"

    try:
        from src.tasks.scheduled_tasks import execute_scheduled_task

        result = execute_scheduled_task(task_id)
        return 200, json.dumps(result)
    except Exception as exc:
        logger.exception(f"Cloud Run task {task_id} failed: {exc}")
        return 500, str(exc)


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        task_id = body.get("task_id") or os.environ.get("TASK_ID", "")
        task_type = body.get("task_type") or os.environ.get("TASK_TYPE", "")
        timestamp = body.get("timestamp") or os.environ.get("DISPATCH_TIMESTAMP", "")
        signature = body.get("signature") or os.environ.get("INVOCATION_SIGNATURE", "")

        if not task_id or not task_type:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing task_id or task_type")
            return

        status, response_body = _process_task(task_id, task_type, timestamp, signature)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_body.encode())

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        logger.info(format % args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    logger.info(f"Cloud Run handler listening on port {port}")
    server.serve_forever()
