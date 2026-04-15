"""
FargateComputeBackend — AWS Fargate compute backend (coming soon).

Architecture (when implemented):
  - Each conversation starts an ECS Fargate task (a serverless container).
  - No 15-minute limit (unlike Lambda) — ideal for long-running agent tasks.
  - Workspace stored on EFS or S3, mounted into the task.
  - Cold start: ~20-40 seconds (mitigated with container image caching).
  - Pay per vCPU/memory per second of task runtime.

Required config (stored encrypted in TenantComputeConfig.fargate_config):
  {
    "region":               "us-east-1",
    "cluster_arn":          "arn:aws:ecs:...",
    "task_definition_arn":  "arn:aws:ecs:...",
    "subnet_ids":           ["subnet-aaa", "subnet-bbb"],
    "security_group_ids":   ["sg-xxx"],
    "s3_bucket":            "my-agent-workspaces",
    "access_key_id":        "AKIA...",
    "secret_access_key":    "..."
  }
"""

import logging

from src.services.compute.backends.base import ComputeBackend
from src.services.compute.session import ComputeSession

logger = logging.getLogger(__name__)

_NOT_IMPLEMENTED_MSG = (
    "AWS Fargate compute backend is not yet implemented. "
    "Use 'docker' backend for self-hosted deployments, "
    "or 'aws_lambda' for short serverless tasks."
)


class FargateComputeBackend(ComputeBackend):
    """
    AWS Fargate compute backend — interface ready, implementation pending.
    """

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    @property
    def backend_type(self) -> str:
        return "aws_fargate"

    async def checkout_session(
        self,
        agent_id: str,
        tenant_id: str,
        conversation_id: str,
    ) -> ComputeSession:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)

    async def return_session(self, session: ComputeSession) -> None:
        await session.close()
