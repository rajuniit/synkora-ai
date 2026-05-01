"""DigitalOcean Functions execution backend."""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from .base import BaseExecutionBackend

logger = logging.getLogger(__name__)

class DOFunctionsBackend(BaseExecutionBackend):
    """
    Dispatch agent tasks to DigitalOcean Functions via async HTTP invocation.

    DO Functions are invoked via a web endpoint URL.  Since Synkora runs on
    DigitalOcean Kubernetes (DKS), this is the native serverless option.

    All credentials are read from platform-level environment variables (DOConfig).
    Set DO_FUNCTIONS_ENDPOINT, DO_API_TOKEN, and DO_FUNCTIONS_INVOCATION_SECRET
    in your deployment environment.  No per-agent credentials are stored or used.

    Invocation model:
        POST {DO_FUNCTIONS_ENDPOINT}
        Authorization: Basic {base64(api_key:"")}
        Body: {"task_id": "...", "task_type": "...", ...}

    DO Functions return HTTP 200 with {"body": ...} on success.
    The invocation is synchronous from DO's side but the function runs
    in a separate isolated container — Celery is freed immediately after
    the HTTP call returns the 200 acknowledgement.

    Note: DO Functions has a 15-minute hard execution limit. Autonomous agents
    that run longer than 15 minutes will be killed. Use cloud_run for agents
    that need unlimited runtime.
    """

    def __init__(self) -> None:
        from src.config.settings import settings

        # Full HTTPS endpoint URL for the function — e.g.
        # https://faas-nyc1-1234abcd.doserverless.co/api/v1/web/fn-xxx/synkora/agent-runner
        self._endpoint = settings.do_functions_endpoint or ""
        self._api_token = settings.do_api_token or ""
        self._invocation_secret = settings.do_functions_invocation_secret

    def is_supported_task_type(self, task_type: str) -> bool:
        return True  # All task types supported; operator accepts the 15-min limit

    def validate(self) -> None:
        """Raise ValueError if required platform config is missing."""
        missing = [k for k, v in {
            "DO_FUNCTIONS_ENDPOINT": self._endpoint,
            "DO_API_TOKEN": self._api_token,
        }.items() if not v]
        if missing:
            raise ValueError(
                f"DigitalOcean Functions backend missing required platform config: {missing}. "
                "Set these environment variables on the platform (operator configuration)."
            )

    async def dispatch(self, task_id: str, task_type: str, agent_id: str, tenant_id: str) -> str:
        """
        Invoke the DO Function via HTTP.  Returns the DO request ID header.

        DO Functions are synchronous from the caller's perspective — the HTTP
        response comes back when the function starts (not when it finishes).
        We use a fire-and-forget approach by checking for a 200 acknowledgement.
        """
        try:
            import httpx  # already in deps (used elsewhere in the codebase)
        except ImportError as exc:
            raise ImportError(
                "httpx is required for the DO Functions backend. "
                "Install it with: pip install httpx"
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

        import base64 as _b64

        auth_header = _b64.b64encode(f"{self._api_token}:".encode()).decode()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._endpoint,
                json=payload,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code not in (200, 202):
            raise RuntimeError(
                f"DO Functions invocation failed: HTTP {response.status_code} — {response.text[:200]}"
            )

        request_id: str = response.headers.get("x-request-id", "")
        logger.info(
            f"DO Functions dispatch: task={task_id} endpoint={self._endpoint} request_id={request_id}"
        )
        return request_id

    def _sign_payload(self, task_id: str, timestamp: str) -> str:
        message = f"{task_id}:{timestamp}".encode()
        return hmac.new(self._invocation_secret.encode(), message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(task_id: str, timestamp: str, signature: str, secret: str) -> bool:
        message = f"{task_id}:{timestamp}".encode()
        expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
