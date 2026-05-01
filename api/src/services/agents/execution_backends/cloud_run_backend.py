"""Google Cloud Run Jobs execution backend."""

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from .base import BaseExecutionBackend

logger = logging.getLogger(__name__)


class CloudRunBackend(BaseExecutionBackend):
    """
    Dispatch agent tasks to Google Cloud Run Jobs.

    All credentials are read from platform-level environment variables (GCPConfig).
    Set GCP_PROJECT_ID, GCP_SERVICE_ACCOUNT_JSON (base64-encoded), GCP_REGION,
    CLOUD_RUN_JOB_NAME, and CLOUD_RUN_INVOCATION_SECRET in your deployment environment.
    No per-agent credentials are stored or used.
    """

    def __init__(self) -> None:
        from src.config.settings import settings

        self._job_name = settings.cloud_run_job_name or ""
        self._project_id = settings.gcp_project_id or ""
        self._region = settings.gcp_region
        self._service_account_json_b64 = settings.gcp_service_account_json or ""
        self._invocation_secret = settings.cloud_run_invocation_secret

    def is_supported_task_type(self, task_type: str) -> bool:
        return True

    def validate(self) -> None:
        """Raise ValueError if required platform config is missing."""
        missing = [
            k
            for k, v in {
                "CLOUD_RUN_JOB_NAME": self._job_name,
                "GCP_PROJECT_ID": self._project_id,
                "GCP_SERVICE_ACCOUNT_JSON": self._service_account_json_b64,
            }.items()
            if not v
        ]
        if missing:
            raise ValueError(
                f"Cloud Run backend missing required platform config: {missing}. "
                "Set these environment variables on the platform (operator configuration)."
            )

    async def dispatch(self, task_id: str, task_type: str, agent_id: str, tenant_id: str) -> str:
        """Create a Cloud Run Job execution. Returns the operation name."""
        try:
            from google.cloud import run_v2  # type: ignore[import-untyped]
            from google.oauth2 import service_account  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-run and google-auth are required for the Cloud Run backend. "
                "Install with: pip install google-cloud-run google-auth"
            ) from exc

        self.validate()

        timestamp = datetime.now(UTC).isoformat()
        env_overrides = [
            {"name": "TASK_ID", "value": task_id},
            {"name": "TASK_TYPE", "value": task_type},
            {"name": "AGENT_ID", "value": agent_id},
            {"name": "TENANT_ID", "value": tenant_id},
            {"name": "DISPATCH_TIMESTAMP", "value": timestamp},
        ]

        if self._invocation_secret:
            env_overrides.append({"name": "INVOCATION_SIGNATURE", "value": self._sign_payload(task_id, timestamp)})

        sa_json = json.loads(base64.b64decode(self._service_account_json_b64).decode())
        credentials = service_account.Credentials.from_service_account_info(
            sa_json, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        client = run_v2.JobsClient(credentials=credentials)
        job_path = client.job_path(self._project_id, self._region, self._job_name)

        request = run_v2.RunJobRequest(
            name=job_path,
            overrides=run_v2.RunJobRequest.Overrides(
                container_overrides=[
                    run_v2.RunJobRequest.Overrides.ContainerOverride(
                        env=[run_v2.EnvVar(name=e["name"], value=e["value"]) for e in env_overrides]
                    )
                ]
            ),
        )
        operation = client.run_job(request=request)
        op_name: str = operation.operation.name if hasattr(operation, "operation") else str(operation)
        logger.info(f"Cloud Run dispatch: task={task_id} job={self._job_name} operation={op_name}")
        return op_name

    def _sign_payload(self, task_id: str, timestamp: str) -> str:
        message = f"{task_id}:{timestamp}".encode()
        return hmac.new(self._invocation_secret.encode(), message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(task_id: str, timestamp: str, signature: str, secret: str) -> bool:
        message = f"{task_id}:{timestamp}".encode()
        expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
