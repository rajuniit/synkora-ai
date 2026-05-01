"""
SAML 2.0 SSO endpoints.

Public endpoints (no auth required):
  GET  /console/api/auth/saml/{tenant_id}/metadata  — SP metadata XML
  GET  /console/api/auth/saml/{tenant_id}/login     — Initiate SSO redirect to IdP
  POST /console/api/auth/saml/{tenant_id}/acs       — ACS callback (assertion consumer)

Authenticated admin endpoints:
  GET    /api/v1/saml/config                        — Read tenant SAML config
  POST   /api/v1/saml/config                        — Create or update SAML config
  DELETE /api/v1/saml/config                        — Delete SAML config
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel as PydanticModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id, require_role
from src.models.tenant import AccountRole
from src.services.saml_service import SAMLService
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)

saml_router = APIRouter()

# ---------------------------------------------------------------------------
# Cookie / session constants (mirror auth.py)
# ---------------------------------------------------------------------------
try:
    from src.config import settings as _settings

    _COOKIE_SECURE = _settings.is_production
    _COOKIE_DOMAIN = _settings.cookie_domain if hasattr(_settings, "cookie_domain") else None
except Exception:
    _COOKIE_SECURE = False
    _COOKIE_DOMAIN = None


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SAMLConfigCreateRequest(PydanticModel):
    """Payload for creating or updating a SAML config."""

    idp_metadata_url: str | None = None
    idp_metadata_xml: str | None = None
    sp_entity_id: str
    acs_url: str
    email_attribute: str = "email"
    name_attribute: str | None = "displayName"
    jit_provisioning: bool = True
    force_saml: bool = False
    is_active: bool = True


class SAMLConfigResponse(PydanticModel):
    """Public representation of a SAML config (no secrets)."""

    id: str
    tenant_id: str
    idp_metadata_url: str | None
    sp_entity_id: str
    acs_url: str
    email_attribute: str
    name_attribute: str | None
    jit_provisioning: bool
    force_saml: bool
    is_active: bool
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Helper: sanitize RelayState to prevent open-redirect and DoS
# ---------------------------------------------------------------------------

_RELAY_STATE_MAX_LEN = 2048
_RELAY_STATE_DEFAULT = "/dashboard"


def _sanitize_relay_state(value: str | None) -> str:
    if not value:
        return _RELAY_STATE_DEFAULT
    # Cap length to prevent DoS via oversized values
    if len(value) > _RELAY_STATE_MAX_LEN:
        return _RELAY_STATE_DEFAULT
    # Reject protocol-relative URLs (//attacker.com) and absolute URLs (http://)
    if value.startswith("//") or "://" in value:
        return _RELAY_STATE_DEFAULT
    # Must be a relative path starting with /
    if not value.startswith("/"):
        return _RELAY_STATE_DEFAULT
    return value


# ---------------------------------------------------------------------------
# Helper: look up tenant by UUID string in URL path
# ---------------------------------------------------------------------------

async def _resolve_tenant_id(tenant_id: str, db: AsyncSession) -> uuid.UUID:
    """Parse and validate the UUID tenant_id path parameter."""
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tenant_id: {tenant_id!r}",
        )


# ---------------------------------------------------------------------------
# Public: SP metadata
# ---------------------------------------------------------------------------

@saml_router.get("/console/api/auth/saml/{tenant_id}/metadata")
async def saml_metadata(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Return the SP (Service Provider) metadata XML for the given tenant.

    Identity Providers import this XML to establish trust with this SP.
    Content-Type is always application/xml.
    """
    tid = await _resolve_tenant_id(tenant_id, db)
    metadata_xml = await SAMLService.get_sp_metadata(db, tid)
    return Response(content=metadata_xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# Public: Initiate SSO
# ---------------------------------------------------------------------------

@saml_router.get("/console/api/auth/saml/{tenant_id}/login")
async def saml_login(
    tenant_id: str,
    relay_state: str | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> RedirectResponse:
    """
    Redirect the browser to the IdP SSO endpoint.

    The optional `relay_state` query parameter is passed through the IdP and
    returned in the ACS POST, allowing the frontend to restore navigation state
    after a successful login.
    """
    tid = await _resolve_tenant_id(tenant_id, db)
    safe_relay_state = _sanitize_relay_state(relay_state)
    sso_url = await SAMLService.initiate_sso(db, tid, relay_state=safe_relay_state)
    return RedirectResponse(url=sso_url, status_code=status.HTTP_302_FOUND)


# ---------------------------------------------------------------------------
# Public: ACS callback
# ---------------------------------------------------------------------------

@saml_router.post("/console/api/auth/saml/{tenant_id}/acs")
async def saml_acs(
    tenant_id: str,
    SAMLResponse: str = Form(...),
    RelayState: str | None = Form(default=None),
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Assertion Consumer Service endpoint.

    The IdP POSTs the signed SAML assertion here after the user authenticates.
    On success, a session is created and the browser is redirected to the frontend
    with the access token embedded in the redirect URL fragment.
    """
    tid = await _resolve_tenant_id(tenant_id, db)

    # 1. Validate the SAML assertion
    user_info = await SAMLService.process_response(
        db,
        tenant_id=tid,
        saml_response=SAMLResponse,
        relay_state=RelayState,
    )

    # 2. Fetch the SAML config to determine JIT behaviour
    saml_config = await SAMLService.get_saml_config(db, tid)
    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML config not found",
        )

    # 3. JIT provisioning / account lookup
    account = await SAMLService.get_or_create_account(
        db,
        tenant_id=tid,
        email=user_info["email"],
        name=user_info["name"],
        jit=saml_config.jit_provisioning,
    )

    # 4. Commit the JIT changes before creating the session
    await db.commit()

    # 5. Create a session (mirrors the standard login flow)
    session_data = await SessionService.create_session(db, account, tid)
    await db.commit()

    # 6. Determine frontend redirect destination
    try:
        from src.config import settings as app_settings

        frontend_base = app_settings.app_base_url or "http://localhost:3005"
    except Exception:
        frontend_base = "http://localhost:3005"

    # Use RelayState as the post-login redirect path if it is a safe relative URL
    redirect_path = _sanitize_relay_state(RelayState)

    # Pass the access token as a fragment parameter so it stays in JS memory
    access_token = session_data["access_token"]
    redirect_url = f"{frontend_base.rstrip('/')}{redirect_path}#saml_token={access_token}"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # Store refresh token in HttpOnly cookie — same settings as the standard login
    response.set_cookie(
        key="refresh_token",
        value=session_data["refresh_token"],
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="strict",
        max_age=30 * 24 * 3600,
        path="/console/api/auth/refresh",
        domain=_COOKIE_DOMAIN,
    )

    return response


# ---------------------------------------------------------------------------
# Public: Single Logout Service (SLO) endpoint
# ---------------------------------------------------------------------------


@saml_router.post("/console/api/auth/saml/{tenant_id}/slo")
async def saml_slo(
    tenant_id: str,
    SAMLResponse: str | None = Form(default=None),
    SAMLRequest: str | None = Form(default=None),
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """
    Single Logout Service endpoint.

    Handles two cases:
      - IdP-initiated logout response: IdP POSTs a SAMLResponse after completing
        logout on its side.
      - IdP-initiated logout request: IdP POSTs a SAMLRequest asking the SP to
        log out the named user.

    In both cases we revoke all active sessions for users of the given tenant and
    redirect to the frontend login page.
    """
    tid = await _resolve_tenant_id(tenant_id, db)

    if not SAMLResponse and not SAMLRequest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAMLResponse or SAMLRequest form field is required",
        )

    # Attempt to extract the email from the SAMLRequest (IdP logout request) so we can
    # target the specific account.  This is best-effort; on failure we fall through to
    # the generic tenant-wide session revocation path.
    account_to_revoke = None
    if SAMLRequest:
        try:
            import base64
            import zlib

            decoded = base64.b64decode(SAMLRequest)
            # SAMLRequests sent via HTTP-POST are not deflated, but try deflate first.
            try:
                xml_bytes = zlib.decompress(decoded, -15)
            except zlib.error:
                xml_bytes = decoded

            import re as _re
            from sqlalchemy import select as _select

            from src.models.tenant import Account as _Account, TenantAccountJoin as _TAJ

            email_match = _re.search(
                rb"<(?:[^:>]+:)?NameID[^>]*>([^<]+)</",
                xml_bytes,
                _re.IGNORECASE,
            )
            if email_match:
                email_str = email_match.group(1).decode(errors="replace").strip()
                result = await db.execute(
                    _select(_Account)
                    .join(_TAJ, _TAJ.account_id == _Account.id)
                    .filter(_Account.email == email_str, _TAJ.tenant_id == tid)
                )
                account_to_revoke = result.scalar_one_or_none()
        except Exception:
            logger.warning("SAML SLO: could not parse SAMLRequest to extract NameID", exc_info=True)

    if account_to_revoke is not None:
        try:
            await SessionService.revoke_session(db, account_id=account_to_revoke.id)
            await db.commit()
            logger.info("SAML SLO: revoked sessions for account %s (tenant %s)", account_to_revoke.id, tid)
        except Exception:
            logger.warning("SAML SLO: failed to revoke sessions for account %s", account_to_revoke.id, exc_info=True)
    else:
        # Could not identify a specific account — log a warning.
        # Deliberately avoid revoking ALL tenant sessions on an unauthenticated POST
        # to prevent a DoS attack that logs out all users.
        logger.warning(
            "SAML SLO: could not identify account for tenant %s from SLO request; "
            "no sessions revoked (provide a valid SAMLRequest with NameID to revoke a specific session)",
            tid,
        )

    try:
        from src.config import settings as app_settings

        frontend_base = app_settings.app_base_url or "http://localhost:3005"
    except Exception:
        frontend_base = "http://localhost:3005"

    return RedirectResponse(
        url=f"{frontend_base.rstrip('/')}/signin?slo=1",
        status_code=status.HTTP_302_FOUND,
    )


# ---------------------------------------------------------------------------
# Authenticated: read config
# ---------------------------------------------------------------------------

@saml_router.get("/api/v1/saml/config")
async def get_saml_config(
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: None = Depends(require_role(AccountRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Return the SAML config for the calling account's tenant.

    Requires ADMIN or OWNER role.
    Returns 404 if no SAML config exists yet.
    """
    saml_config = await SAMLService.get_saml_config(db, tenant_id)
    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SAML configuration found for this tenant",
        )
    return _serialize_config(saml_config)


# ---------------------------------------------------------------------------
# Authenticated: create / update config
# ---------------------------------------------------------------------------

@saml_router.post("/api/v1/saml/config", status_code=status.HTTP_200_OK)
async def upsert_saml_config(
    data: SAMLConfigCreateRequest,
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: None = Depends(require_role(AccountRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Create or update the SAML configuration for the calling account's tenant.

    Requires ADMIN or OWNER role.
    Exactly one of `idp_metadata_url` or `idp_metadata_xml` must be provided.
    """
    from src.models.saml_config import SAMLConfig

    if not data.idp_metadata_url and not data.idp_metadata_xml:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either idp_metadata_url or idp_metadata_xml",
        )

    saml_config = await SAMLService.get_saml_config(db, tenant_id)

    if saml_config is None:
        saml_config = SAMLConfig(tenant_id=tenant_id)
        db.add(saml_config)

    saml_config.idp_metadata_url = data.idp_metadata_url
    saml_config.idp_metadata_xml = data.idp_metadata_xml
    saml_config.sp_entity_id = data.sp_entity_id
    saml_config.acs_url = data.acs_url
    saml_config.email_attribute = data.email_attribute
    saml_config.name_attribute = data.name_attribute
    saml_config.jit_provisioning = data.jit_provisioning
    saml_config.force_saml = data.force_saml
    saml_config.is_active = data.is_active

    await db.commit()
    await db.refresh(saml_config)

    return _serialize_config(saml_config)


# ---------------------------------------------------------------------------
# Authenticated: delete config
# ---------------------------------------------------------------------------

@saml_router.delete("/api/v1/saml/config", status_code=status.HTTP_200_OK)
async def delete_saml_config(
    current_account=Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: None = Depends(require_role(AccountRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Delete the SAML configuration for the calling account's tenant.

    Requires ADMIN or OWNER role.
    Returns 404 if no config exists.
    """
    saml_config = await SAMLService.get_saml_config(db, tenant_id)
    if not saml_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SAML configuration found for this tenant",
        )

    await db.delete(saml_config)
    await db.commit()

    return {"success": True, "message": "SAML configuration deleted"}


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def _serialize_config(saml_config) -> dict:
    """Convert a SAMLConfig model instance to a JSON-safe dict."""
    return {
        "id": str(saml_config.id),
        "tenant_id": str(saml_config.tenant_id),
        "idp_metadata_url": saml_config.idp_metadata_url,
        # Deliberately omit idp_metadata_xml to avoid leaking large blobs;
        # callers that need it can fetch via the admin API directly.
        "has_idp_metadata_xml": bool(saml_config.idp_metadata_xml),
        "sp_entity_id": saml_config.sp_entity_id,
        "acs_url": saml_config.acs_url,
        "email_attribute": saml_config.email_attribute,
        "name_attribute": saml_config.name_attribute,
        "jit_provisioning": saml_config.jit_provisioning,
        "force_saml": saml_config.force_saml,
        "is_active": saml_config.is_active,
        "created_at": saml_config.created_at.isoformat() if saml_config.created_at else None,
        "updated_at": saml_config.updated_at.isoformat() if saml_config.updated_at else None,
    }
