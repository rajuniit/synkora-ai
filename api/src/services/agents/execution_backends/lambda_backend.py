"""AWS Lambda execution backend."""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from .base import BaseExecutionBackend

logger = logging.getLogger(__name__)


class LambdaBackend(BaseExecutionBackend):
    """
    Dispatch agent tasks to AWS Lambda via async invocation.

    All credentials are read from platform-level environment variables (AWSConfig).
    Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_LAMBDA_FUNCTION_ARN,
    AWS_REGION, and LAMBDA_INVOCATION_SECRET in your deployment environment.
    No per-agent credentials are stored or used.

    Note: Lambda has a 15-minute hard execution limit. Autonomous agents that run
    longer than 15 minutes will be killed by AWS. Use cloud_run for agents that
    need unlimited runtime.
    """

    def __init__(self) -> None:
        from src.config.settings import settings

        self._function_arn = settings.aws_lambda_function_arn or ""
        self._region = settings.aws_region
        self._access_key = settings.aws_access_key_id or ""
        self._secret_key = settings.aws_secret_access_key or ""
        self._invocation_secret = settings.lambda_invocation_secret

    def is_supported_task_type(self, task_type: str) -> bool:
        return True  # All task types supported; operator accepts the 15-min limit

    def validate(self) -> None:
        """Raise ValueError if required platform config is missing."""
        missing = [
            k
            for k, v in {
                "AWS_LAMBDA_FUNCTION_ARN": self._function_arn,
                "AWS_ACCESS_KEY_ID": self._access_key,
                "AWS_SECRET_ACCESS_KEY": self._secret_key,
            }.items()
            if not v
        ]
        if missing:
            raise ValueError(
                f"Lambda backend missing required platform config: {missing}. "
                "Set these environment variables on the platform (operator configuration)."
            )

    async def dispatch(self, task_id: str, task_type: str, agent_id: str, tenant_id: str) -> str:
        """Invoke Lambda asynchronously. Returns the invocation request ID."""
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for the Lambda execution backend. Install it with: pip install boto3"
            ) from exc

        self.validate()

        timestamp = datetime.now(UTC).isoformat()
        payload: dict = {
            "task_id": task_id,
            "task_type": task_type,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "timestamp": timestamp,
        }

        if self._invocation_secret:
            payload["signature"] = self._sign_payload(task_id, timestamp)

        client = boto3.client(
            "lambda",
            region_name=self._region,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )
        response = client.invoke(
            FunctionName=self._function_arn,
            InvocationType="Event",  # async — fire and forget
            Payload=json.dumps(payload).encode(),
        )
        request_id: str = response.get("ResponseMetadata", {}).get("RequestId", "")
        logger.info(f"Lambda dispatch: task={task_id} arn={self._function_arn} request_id={request_id}")
        return request_id

    def _sign_payload(self, task_id: str, timestamp: str) -> str:
        message = f"{task_id}:{timestamp}".encode()
        return hmac.new(self._invocation_secret.encode(), message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(task_id: str, timestamp: str, signature: str, secret: str) -> bool:
        message = f"{task_id}:{timestamp}".encode()
        expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
