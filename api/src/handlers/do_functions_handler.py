"""
DigitalOcean Functions entry point for agent task execution.

DO Functions use a specific interface: a `main(args)` function that receives
the request body as a dict and returns a dict with an optional `body` key.

All task types are supported; the operator accepts the 15-minute DO
Functions execution limit for autonomous agents.

Security:
- Verifies HMAC-SHA256 signature on every invocation.
- All secrets (DB URL, LLM API keys) are injected as DO Function env vars
  via DigitalOcean Secrets — never passed in the invocation payload.
- The invocation payload contains only IDs, never user data or credentials.

Deployment:
  1. Build project.yml pointing to this file as the function entrypoint
  2. Set SYNKORA_DIRECT_EXECUTION=true in the function's environment
  3. Set all required env vars (DATABASE_URL, etc.) via DO Secrets
  4. Deploy: doctl serverless deploy .

Runtime: python:3.11
Memory: 4096MB (set in project.yml)
Timeout: 900s (set in project.yml)
"""

import json
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(args: dict) -> dict:
    """
    DigitalOcean Functions entry point.

    Expected args schema:
        {
          "task_id": "...",
          "task_type": "agent_task" | "database_query",
          "agent_id": "...",
          "tenant_id": "...",
          "timestamp": "ISO-8601",
          "signature": "HMAC-SHA256 hex"   # required when DO_FUNCTIONS_INVOCATION_SECRET is set
        }
    """
    task_id = args.get("task_id")
    task_type = args.get("task_type")
    timestamp = args.get("timestamp", "")
    signature = args.get("signature", "")

    if not task_id or not task_type:
        logger.error("Missing task_id or task_type in DO Functions invocation")
        return {"statusCode": 400, "body": json.dumps({"error": "Missing required fields"})}

    # Verify HMAC signature if secret is configured
    secret = os.environ.get("DO_FUNCTIONS_INVOCATION_SECRET")
    if secret:
        from src.services.agents.execution_backends.do_functions_backend import DOFunctionsBackend

        if not signature:
            logger.error(f"Missing signature for task {task_id}")
            return {"statusCode": 403, "body": json.dumps({"error": "Missing invocation signature"})}

        if not DOFunctionsBackend.verify_signature(task_id, timestamp, signature, secret):
            logger.error(f"Invalid signature for task {task_id}")
            return {"statusCode": 403, "body": json.dumps({"error": "Invalid invocation signature"})}

    # SYNKORA_DIRECT_EXECUTION=true must be set in the function's env to prevent
    # the task executor from trying to dispatch to DO Functions again (infinite loop).
    if not os.environ.get("SYNKORA_DIRECT_EXECUTION"):
        logger.error("SYNKORA_DIRECT_EXECUTION env var not set — refusing to execute to prevent dispatch loop")
        return {"statusCode": 500, "body": json.dumps({"error": "SYNKORA_DIRECT_EXECUTION not set"})}

    logger.info(f"DO Functions executing task {task_id} (type={task_type})")

    try:
        from src.tasks.scheduled_tasks import execute_scheduled_task

        result = execute_scheduled_task(task_id)
        logger.info(f"DO Functions task {task_id} completed: {json.dumps(result)[:200]}")
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as exc:
        logger.exception(f"DO Functions task {task_id} failed: {exc}")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
