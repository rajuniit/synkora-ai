"""
LambdaComputeBackend — AWS Lambda compute backend (coming soon).

Architecture (when implemented):
  - Each exec_command invocation calls a Lambda function synchronously.
  - Agent workspace is stored in an S3 bucket (synced at conversation start/end).
  - Scales to millions of concurrent agents; pay-per-invocation, no idle cost.
  - Cold start: ~200ms (mitigated with Lambda SnapStart / provisioned concurrency).
  - 15-minute hard limit per invocation (use Fargate for long-running tasks).

Required config (stored encrypted in TenantComputeConfig.lambda_config):
  {
    "region":            "us-east-1",
    "function_arn":      "arn:aws:lambda:...",
    "s3_bucket":         "my-agent-workspaces",
    "access_key_id":     "AKIA...",
    "secret_access_key": "..."
  }
"""

import logging

from src.services.compute.backends.base import ComputeBackend
from src.services.compute.session import ComputeSession

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_MSG = (
    "AWS Lambda compute backend is not yet implemented. "
    "Configure 'docker' backend for self-hosted deployments, "
    "or 'aws_fargate' for long-running serverless tasks."
)


class LambdaComputeBackend(ComputeBackend):
    """
    AWS Lambda compute backend — interface ready, implementation pending.

    The interface is stable so tenants can configure Lambda credentials now;
    the actual invocation logic will be added in a future release.
    """

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    @property
    def backend_type(self) -> str:
        return "aws_lambda"

    async def checkout_session(
        self,
        agent_id: str,
        tenant_id: str,
        conversation_id: str,
    ) -> ComputeSession:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def return_session(self, session: ComputeSession) -> None:
        await session.close()
