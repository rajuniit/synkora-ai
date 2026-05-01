"""
SAML 2.0 SSO service.

Wraps the python3-saml (OneLogin) library to provide:
- SP metadata generation
- SSO redirect initiation
- ACS response validation
- JIT account provisioning
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guard
# ---------------------------------------------------------------------------
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    _SAML_AVAILABLE = True
except ImportError:
    _SAML_AVAILABLE = False
    logger.warning("python3-saml not installed — SAML SSO endpoints will return 503")


def _require_saml() -> None:
    """Raise HTTP 503 if python3-saml is not installed."""
    if not _SAML_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML SSO is not available (python3-saml not installed)",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sp_base_url() -> str:
    """Return the SP base URL from settings or fallback env var."""
    try:
        from src.config.settings import settings as app_settings

        if app_settings.app_base_url:
            return app_settings.app_base_url.rstrip("/")
    except Exception:
        pass
    return os.getenv("APP_BASE_URL", "http://localhost:5001").rstrip("/")


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------

class SAMLService:
    """Service layer for SAML 2.0 SSO operations."""

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_saml_config(db: AsyncSession, tenant_id: uuid.UUID):
        """Return the active SAMLConfig for a tenant, or None."""
        from src.models.saml_config import SAMLConfig

        result = await db.execute(
            select(SAMLConfig).where(
                SAMLConfig.tenant_id == tenant_id,
                SAMLConfig.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_saml_config_by_tenant_name(db: AsyncSession, tenant_name: str):
        """Return the active SAMLConfig looked up via tenant name, or None."""
        from src.models.saml_config import SAMLConfig
        from src.models.tenant import Tenant

        result = await db.execute(
            select(SAMLConfig)
            .join(Tenant, Tenant.id == SAMLConfig.tenant_id)
            .where(
                Tenant.name == tenant_name,
                SAMLConfig.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # python3-saml settings dict
    # ------------------------------------------------------------------

    @staticmethod
    def get_settings(saml_config) -> dict:
        """
        Build the python3-saml settings dict from a SAMLConfig record.

        IdP metadata can be provided as a URL (resolved lazily by python3-saml)
        or as raw XML embedded in the config record.
        """
        _require_saml()

        sp_base = _get_sp_base_url()
        tenant_id_str = str(saml_config.tenant_id)

        saml_settings: dict = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": saml_config.sp_entity_id,
                "assertionConsumerService": {
                    "url": saml_config.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": f"{sp_base}/console/api/auth/saml/{tenant_id_str}/slo",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": "",
                "privateKey": "",
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": True,
                "wantAttributeStatement": True,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "metadataValidUntil": None,
                "metadataCacheDuration": None,
            },
        }

        # IdP block — prefer inline XML so no outbound HTTP is needed at auth time
        if saml_config.idp_metadata_xml:
            # Parse raw XML into the dict python3-saml expects
            idp_data = OneLogin_Saml2_Settings.parse_remote_metadata(
                saml_config.idp_metadata_xml.encode("utf-8")
            )
            saml_settings["idp"] = idp_data
        elif saml_config.idp_metadata_url:
            # python3-saml will fetch and parse the URL when loading settings
            saml_settings["idp"] = {
                "entityId": "",
                "singleSignOnService": {"url": "", "binding": ""},
                "x509cert": "",
            }
            saml_settings["remote"] = {
                "metadataUrl": saml_config.idp_metadata_url,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SAML config has neither idp_metadata_url nor idp_metadata_xml",
            )

        return saml_settings

    # ------------------------------------------------------------------
    # SSO flow
    # ------------------------------------------------------------------

    @staticmethod
    async def initiate_sso(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        relay_state: str | None = None,
    ) -> str:
        """
        Build and return the IdP SSO redirect URL for the given tenant.

        Args:
            db: Async DB session
            tenant_id: Tenant to authenticate against
            relay_state: Optional opaque relay state passed through the IdP

        Returns:
            URL string to redirect the browser to
        """
        _require_saml()

        saml_config = await SAMLService.get_saml_config(db, tenant_id)
        if not saml_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML SSO is not configured for this tenant",
            )

        saml_settings = SAMLService.get_settings(saml_config)
        auth = OneLogin_Saml2_Auth(
            # python3-saml needs a request dict; minimal version for redirect-only
            {"https": "on", "http_host": _get_sp_base_url().split("//")[-1], "script_name": "/", "get_data": {}, "post_data": {}},
            old_settings=saml_settings,
        )
        return auth.login(return_to=relay_state)

    @staticmethod
    async def process_response(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        saml_response: str,
        relay_state: str | None = None,
    ) -> dict:
        """
        Validate a SAML response POSTed to the ACS endpoint.

        Args:
            db: Async DB session
            tenant_id: Tenant being authenticated
            saml_response: Base64-encoded SAMLResponse POST parameter
            relay_state: Relay state from the POST parameter

        Returns:
            Dict with keys: email, name, attributes

        Raises:
            HTTPException 401 if the assertion is invalid
        """
        _require_saml()

        saml_config = await SAMLService.get_saml_config(db, tenant_id)
        if not saml_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML SSO is not configured for this tenant",
            )

        saml_settings = SAMLService.get_settings(saml_config)

        sp_host = _get_sp_base_url().split("//")[-1]
        request_data = {
            "https": "on",
            "http_host": sp_host,
            "script_name": saml_config.acs_url,
            "get_data": {},
            "post_data": {"SAMLResponse": saml_response},
        }

        auth = OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            logger.warning("SAML assertion errors for tenant %s: %s — %s", tenant_id, errors, auth.get_last_error_reason())
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SAML assertion invalid: {', '.join(errors)}",
            )

        if not auth.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed",
            )

        attributes: dict = auth.get_attributes()
        name_id: str = auth.get_nameid() or ""

        # Resolve email from configured attribute or fall back to NameID
        email_attr = saml_config.email_attribute or "email"
        email = _first_value(attributes.get(email_attr)) or name_id
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SAML response missing email attribute '{email_attr}'",
            )

        name_attr = saml_config.name_attribute or "displayName"
        name = _first_value(attributes.get(name_attr)) or email.split("@")[0]

        return {
            "email": email.lower().strip(),
            "name": name,
            "attributes": attributes,
        }

    # ------------------------------------------------------------------
    # JIT provisioning
    # ------------------------------------------------------------------

    @staticmethod
    async def get_or_create_account(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        email: str,
        name: str,
        jit: bool,
    ):
        """
        Return an existing Account for the given email, or create one via JIT.

        Args:
            db: Async DB session
            tenant_id: Tenant the account belongs to
            email: Email from SAML assertion
            name: Display name from SAML assertion
            jit: Whether JIT provisioning is enabled

        Returns:
            Account instance

        Raises:
            HTTPException 403 if account doesn't exist and JIT is disabled
        """
        from src.models.tenant import Account, AccountRole, AccountStatus, TenantAccountJoin

        # Look up existing account
        result = await db.execute(select(Account).where(Account.email == email))
        account = result.scalar_one_or_none()

        if account is None:
            if not jit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account not found and JIT provisioning is disabled for this tenant",
                )

            # Create account — ACTIVE because IdP has already authenticated the user
            account = Account(
                name=name,
                email=email,
                password_hash="",  # No password for SAML-only accounts
                status=AccountStatus.ACTIVE,
            )
            db.add(account)
            await db.flush()
            logger.info("SAML JIT: created account %s for tenant %s", account.id, tenant_id)

        # Ensure membership in the target tenant
        result = await db.execute(
            select(TenantAccountJoin).where(
                TenantAccountJoin.account_id == account.id,
                TenantAccountJoin.tenant_id == tenant_id,
            )
        )
        membership = result.scalar_one_or_none()

        if membership is None:
            if not jit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is not a member of this tenant and JIT provisioning is disabled",
                )
            membership = TenantAccountJoin(
                tenant_id=tenant_id,
                account_id=account.id,
                role=AccountRole.NORMAL,
            )
            db.add(membership)
            logger.info("SAML JIT: added account %s to tenant %s as NORMAL", account.id, tenant_id)

        await db.flush()
        return account

    # ------------------------------------------------------------------
    # SP metadata
    # ------------------------------------------------------------------

    @staticmethod
    async def get_sp_metadata(db: AsyncSession, tenant_id: uuid.UUID) -> str:
        """
        Generate and return the SP metadata XML for the given tenant.

        Returns:
            XML string

        Raises:
            HTTPException 404 if no SAML config exists
        """
        _require_saml()

        saml_config = await SAMLService.get_saml_config(db, tenant_id)
        if not saml_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML SSO is not configured for this tenant",
            )

        saml_settings_dict = SAMLService.get_settings(saml_config)
        settings_obj = OneLogin_Saml2_Settings(settings=saml_settings_dict, sp_validation_only=True)
        metadata = settings_obj.get_sp_metadata()
        errors = settings_obj.validate_metadata(metadata)
        if errors:
            logger.error("SP metadata validation errors: %s", errors)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"SP metadata generation failed: {', '.join(errors)}",
            )
        return metadata


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _first_value(attr_value) -> str | None:
    """Return the first value from a SAML attribute (which may be a list)."""
    if attr_value is None:
        return None
    if isinstance(attr_value, list):
        return attr_value[0] if attr_value else None
    return str(attr_value)
