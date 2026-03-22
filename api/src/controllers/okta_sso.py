"""
Okta SSO Controllers.

Handles Okta SSO authentication flows for enterprise tenants.
"""

import json
import logging
import secrets
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.config_helper import get_app_base_url

from ..core.database import get_async_db
from ..middleware.auth_middleware import get_current_tenant_id
from ..models.okta_tenant import OktaTenant
from ..services.sso import OktaSSOService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sso/okta", tags=["okta-sso"])

_STATE_TTL = 600  # 10 minutes


def _get_redis():
    try:
        from src.config.redis import get_redis

        redis = get_redis()
        if redis is None:
            raise RuntimeError("Redis returned None")
        return redis
    except Exception as e:
        logger.error(f"Redis unavailable for Okta SSO state: {e}")
        raise RuntimeError("SSO service temporarily unavailable")


def _store_okta_state(state: str, data: dict) -> None:
    _get_redis().setex(f"okta_sso_state:{state}", _STATE_TTL, json.dumps(data))


def _consume_okta_state(state: str) -> dict | None:
    try:
        redis = _get_redis()
        raw = redis.get(f"okta_sso_state:{state}")
        if raw:
            redis.delete(f"okta_sso_state:{state}")
            return json.loads(raw)
        return None
    except RuntimeError:
        return None


# Pydantic models
class OktaTenantCreate(BaseModel):
    okta_domain: str
    client_id: str
    client_secret: str
    redirect_uri: str | None = None
    is_active: bool = True


class OktaTenantUpdate(BaseModel):
    okta_domain: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    is_active: bool | None = None


# Okta SSO Endpoints


@router.get("/login")
async def okta_login(
    tenant_id: str = Query(..., description="Tenant ID for Okta SSO"),
    redirect_url: str = Query(None, description="Frontend redirect URL after login"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Initiate Okta SSO flow for a tenant.

    This endpoint redirects the user to Okta's authorization page.
    """
    try:
        # Get Okta tenant configuration
        tenant_uuid = uuid.UUID(tenant_id)
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_uuid, OktaTenant.is_active))
        okta_tenant = result.scalar_one_or_none()

        if not okta_tenant:
            raise HTTPException(status_code=404, detail="Okta SSO not configured for this tenant")
        base_url = await get_app_base_url(db, tenant_uuid)
        # Initialize SSO service
        sso = OktaSSOService(
            okta_domain=okta_tenant.okta_domain,
            client_id=okta_tenant.client_id,
            client_secret=okta_tenant.client_secret,
            redirect_uri=okta_tenant.redirect_uri,
        )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in Redis
        _store_okta_state(
            state,
            {
                "tenant_id": tenant_id,
                "redirect_url": redirect_url or f"{base_url}/dashboard",
                "flow_type": "okta_sso",
            },
        )

        # Get authorization URL
        auth_url = sso.get_authorization_url(state=state)

        logger.info(f"Initiating Okta SSO for tenant {tenant_id}")

        return RedirectResponse(url=auth_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Okta SSO login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="SSO login failed. Please try again.")


@router.get("/callback")
async def okta_callback(
    code: str = Query(..., description="Authorization code from Okta"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Handle Okta SSO callback.

    This endpoint receives the authorization code from Okta,
    exchanges it for an access token, gets user info, and creates/links account.
    """
    state_data = _consume_okta_state(state)
    try:
        if not state_data:
            raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

        tenant_id = uuid.UUID(state_data["tenant_id"])
        redirect_url = state_data["redirect_url"]

        # Get Okta tenant configuration
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_id, OktaTenant.is_active))
        okta_tenant = result.scalar_one_or_none()

        if not okta_tenant:
            raise HTTPException(status_code=404, detail="Okta SSO not configured for this tenant")

        # Initialize SSO service
        sso = OktaSSOService(
            okta_domain=okta_tenant.okta_domain,
            client_id=okta_tenant.client_id,
            client_secret=okta_tenant.client_secret,
            redirect_uri=okta_tenant.redirect_uri,
        )

        # Exchange code for token
        token_data = await sso.exchange_code(code)

        if not token_data.get("access_token"):
            raise HTTPException(status_code=400, detail="Failed to get access token")

        # Get user info
        user_info = await sso.get_user_info(token_data["access_token"])

        # Extract user details
        user_email = user_info.get("email")
        user_info.get("name")

        if not user_email:
            raise HTTPException(status_code=400, detail="Failed to get user information from Okta")

        # Account creation/linking is handled by the SSO callback in social_auth
        # This endpoint redirects with success message

        logger.info(f"Okta SSO successful for tenant {tenant_id}, user {user_email}")

        return RedirectResponse(url=f"{redirect_url}?login=success&provider=okta&email={user_email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Okta SSO callback error: {e}", exc_info=True)
        fallback = (state_data or {}).get("redirect_url", "/signin")
        return RedirectResponse(
            url=f"{fallback}?login=error&message={quote('SSO sign-in failed. Please try again.', safe='')}"
        )


# Okta Tenant Management Endpoints


@router.get("/config")
async def get_okta_config(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """
    Get Okta SSO configuration for the current tenant.
    """
    try:
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_id))
        okta_tenant = result.scalar_one_or_none()

        if not okta_tenant:
            return {"configured": False}

        return {
            "configured": True,
            "okta_domain": okta_tenant.okta_domain,
            "client_id": okta_tenant.client_id,
            "redirect_uri": okta_tenant.redirect_uri,
            "is_active": okta_tenant.is_active,
            "created_at": okta_tenant.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Get Okta config error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def create_okta_config(
    data: OktaTenantCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create Okta SSO configuration for the current tenant.
    """
    try:
        # Check if configuration already exists
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_id))
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="Okta SSO configuration already exists for this tenant")

        # Create new configuration
        okta_tenant = OktaTenant(
            tenant_id=tenant_id,
            okta_domain=data.okta_domain,
            client_id=data.client_id,
            client_secret=data.client_secret,
            redirect_uri=data.redirect_uri or "http://localhost:8000/api/v1/sso/okta/callback",
            is_active=data.is_active,
        )

        db.add(okta_tenant)
        await db.commit()
        await db.refresh(okta_tenant)

        logger.info(f"Created Okta SSO configuration for tenant {tenant_id}")

        return {
            "success": True,
            "message": "Okta SSO configuration created successfully",
            "okta_domain": okta_tenant.okta_domain,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create Okta config error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_okta_config(
    data: OktaTenantUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update Okta SSO configuration for the current tenant.
    """
    try:
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_id))
        okta_tenant = result.scalar_one_or_none()

        if not okta_tenant:
            raise HTTPException(status_code=404, detail="Okta SSO configuration not found for this tenant")

        # Update fields if provided
        if data.okta_domain is not None:
            okta_tenant.okta_domain = data.okta_domain
        if data.client_id is not None:
            okta_tenant.client_id = data.client_id
        if data.client_secret is not None:
            okta_tenant.client_secret = data.client_secret
        if data.redirect_uri is not None:
            okta_tenant.redirect_uri = data.redirect_uri
        if data.is_active is not None:
            okta_tenant.is_active = data.is_active

        await db.commit()
        await db.refresh(okta_tenant)

        logger.info(f"Updated Okta SSO configuration for tenant {tenant_id}")

        return {"success": True, "message": "Okta SSO configuration updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update Okta config error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config")
async def delete_okta_config(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """
    Delete Okta SSO configuration for the current tenant.
    """
    try:
        result = await db.execute(select(OktaTenant).filter(OktaTenant.tenant_id == tenant_id))
        okta_tenant = result.scalar_one_or_none()

        if not okta_tenant:
            raise HTTPException(status_code=404, detail="Okta SSO configuration not found for this tenant")

        await db.delete(okta_tenant)
        await db.commit()

        logger.info(f"Deleted Okta SSO configuration for tenant {tenant_id}")

        return {"success": True, "message": "Okta SSO configuration deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete Okta config error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
