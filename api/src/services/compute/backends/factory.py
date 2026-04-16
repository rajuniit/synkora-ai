"""
ComputeBackend factory — returns a SandboxComputeBackend for the tenant.
"""

import logging
from typing import Any

from src.services.compute.backends.base import ComputeBackend

logger = logging.getLogger(__name__)


async def get_backend_for_tenant(
    tenant_id: Any,
    db_session: Any,
) -> ComputeBackend:
    from src.config.settings import settings
    from src.services.compute.backends.sandbox_backend import SandboxComputeBackend

    if not settings.sandbox_service_url:
        raise RuntimeError(
            "SANDBOX_SERVICE_URL is not configured. "
            "Ensure the synkora-sandbox service is running and this env var is set."
        )

    return SandboxComputeBackend(
        tenant_id=str(tenant_id),
        sandbox_url=settings.sandbox_service_url,
        sandbox_api_key=settings.sandbox_api_key,
    )
