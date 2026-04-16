"""
Compute status controller.

GET  /api/v1/compute/status — sandbox service availability
POST /api/v1/compute/test   — run a test command in the sandbox
"""

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/compute/status")
async def compute_status(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    import httpx

    from src.config.settings import settings

    sandbox_url = settings.sandbox_service_url
    available = False
    if sandbox_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{sandbox_url.rstrip('/')}/health")
                available = resp.status_code == 200
        except Exception:
            available = False

    return {
        "sandbox_service_url": sandbox_url,
        "sandbox_available": available,
    }


@router.post("/compute/test")
async def compute_test(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    import time

    from src.services.compute.backends.factory import get_backend_for_tenant

    try:
        backend = await get_backend_for_tenant(tenant_id, db)
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}

    t0 = time.monotonic()
    session = None
    try:
        session = await backend.checkout_session(
            agent_id=f"test-{tenant_id}",
            tenant_id=str(tenant_id),
            conversation_id=f"test-{uuid.uuid4()}",
        )
        result = await session.exec_command(["echo", "sandbox-ok"])
        return {
            "success": result["success"],
            "output": result.get("output", "").strip(),
            "error": result.get("error", ""),
            "latency_ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": round((time.monotonic() - t0) * 1000)}
    finally:
        if session is not None:
            try:
                await session.close()
            except Exception:
                pass
