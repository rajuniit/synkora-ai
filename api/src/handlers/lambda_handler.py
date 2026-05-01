"""
AWS Lambda entry point for agent task execution.

The Lambda function runs the same agent logic as the Celery worker but in a
serverless context.  All task types are supported; the operator accepts
Lambda's 15-minute hard execution limit for autonomous agents.

Security:
- Verifies HMAC-SHA256 signature on every invocation.
- All secrets (DB URL, LLM API keys) are injected as Lambda env vars via
  AWS Secrets Manager / IAM — never passed in the event payload.
- The invocation payload contains only IDs, never user data or credentials.

Usage (when deployed as a Lambda function):
  Runtime: Python 3.11
  Handler: src.handlers.lambda_handler.handler
  Environment variables: same as the API container (.env)
"""

import json
import logging
import os
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict, context: object) -> dict:
    """
    Lambda handler entry point.

    Expected event schema:
        {
          "task_id": "...",
          "task_type": "agent_task" | "database_query",
          "agent_id": "...",
          "tenant_id": "...",
          "timestamp": "ISO-8601",
          "signature": "HMAC-SHA256 hex"   # required when LAMBDA_INVOCATION_SECRET is set
        }
    """
    task_id = event.get("task_id")
    task_type = event.get("task_type")
    timestamp = event.get("timestamp", "")
    signature = event.get("signature", "")

    if not task_id or not task_type:
        logger.error("Missing task_id or task_type in event")
        return {"statusCode": 400, "body": "Missing required fields"}

    # Verify HMAC signature if secret is configured
    secret = os.environ.get("LAMBDA_INVOCATION_SECRET")
    if secret:
        from src.services.agents.execution_backends.lambda_backend import LambdaBackend

        if not signature:
            logger.error(f"Missing signature for task {task_id}")
            return {"statusCode": 403, "body": "Missing invocation signature"}

        if not LambdaBackend.verify_signature(task_id, timestamp, signature, secret):
            logger.error(f"Invalid signature for task {task_id}")
            return {"statusCode": 403, "body": "Invalid invocation signature"}

    logger.info(f"Lambda executing task {task_id} (type={task_type})")

    # Set SYNKORA_DIRECT_EXECUTION so the task executor does not try to
    # dispatch back to Lambda — that would cause an infinite invocation loop.
    os.environ["SYNKORA_DIRECT_EXECUTION"] = "true"

    try:
        from src.tasks.scheduled_tasks import execute_scheduled_task

        result = execute_scheduled_task(task_id)
        logger.info(f"Lambda task {task_id} completed: {json.dumps(result)[:200]}")
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as exc:
        logger.exception(f"Lambda task {task_id} failed: {exc}")
        return {"statusCode": 500, "body": str(exc)}
