"""SCIM 2.0 user provisioning service.

Implements RFC 7643 / 7644 operations for User resources.
The SCIM identity maps directly to the platform Account model:
  - SCIM userName  <->  Account.email
  - SCIM id        <->  Account.id (UUID)
  - SCIM active    <->  Account.status == AccountStatus.ACTIVE

All operations are scoped to the tenant_id extracted from the validated SCIM
bearer token, so there is zero risk of cross-tenant data leakage.
"""

import hashlib
import logging
import re
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.scim_token import SCIMToken
from src.models.tenant import Account, AccountRole, AccountStatus, TenantAccountJoin
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SCIM schema URNs
# ---------------------------------------------------------------------------
_SCHEMA_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
_SCHEMA_LIST = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
_SCHEMA_ERROR = "urn:ietf:params:scim:api:messages:2.0:Error"

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a plaintext SCIM token."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_scim_token() -> tuple[str, str]:
    """
    Generate a new SCIM bearer token.

    Returns:
        (plaintext, token_hash) — store only the hash; show plaintext once.
    """
    plaintext = secrets.token_urlsafe(32)
    return plaintext, _hash_token(plaintext)


# ---------------------------------------------------------------------------
# SCIM resource serialisers
# ---------------------------------------------------------------------------


def _account_to_scim(account: Account, tenant_id: uuid.UUID) -> dict:
    """Serialise an Account instance to a SCIM 2.0 User resource dict."""
    active = account.status == AccountStatus.ACTIVE
    created_iso = account.created_at.isoformat() if account.created_at else datetime.now(UTC).isoformat()
    updated_iso = account.updated_at.isoformat() if account.updated_at else created_iso
    return {
        "schemas": [_SCHEMA_USER],
        "id": str(account.id),
        "externalId": str(account.id),
        "userName": account.email,
        "name": {
            "formatted": account.name,
            "givenName": account.name.split(" ", 1)[0] if account.name else "",
            "familyName": account.name.split(" ", 1)[1] if account.name and " " in account.name else "",
        },
        "displayName": account.name,
        "emails": [
            {
                "value": account.email,
                "primary": True,
                "type": "work",
            }
        ],
        "active": active,
        "meta": {
            "resourceType": "User",
            "created": created_iso,
            "lastModified": updated_iso,
            "location": f"/scim/v2/Users/{account.id}",
        },
    }


def _parse_name(scim_data: dict) -> str:
    """Extract a display name string from a SCIM User payload."""
    name_obj = scim_data.get("name", {})
    if name_obj.get("formatted"):
        return name_obj["formatted"]
    given = name_obj.get("givenName", "")
    family = name_obj.get("familyName", "")
    full = f"{given} {family}".strip()
    if full:
        return full
    # Fall back to userName (email prefix)
    username = scim_data.get("userName", "")
    return username.split("@")[0] if "@" in username else username


# ---------------------------------------------------------------------------
# Filter parser — only supports: userName eq "value"
# ---------------------------------------------------------------------------

_FILTER_RE = re.compile(r'^userName\s+eq\s+"([^"]+)"$', re.IGNORECASE)


def _apply_filter(query, filter_str: str | None):
    """Apply a basic SCIM filter to a SQLAlchemy Account query."""
    if not filter_str:
        return query
    m = _FILTER_RE.match(filter_str.strip())
    if m:
        email_value = m.group(1)
        return query.filter(Account.email == email_value)
    # Unsupported filter — return unmodified (caller should handle 400 if strict)
    logger.warning("Unsupported SCIM filter ignored: %s", filter_str)
    return query


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


async def validate_scim_token(db: AsyncSession, token: str) -> SCIMToken | None:
    """
    Validate a SCIM bearer token.

    Hashes the incoming plaintext, looks it up, and updates last_used_at on hit.

    Args:
        db: Async database session
        token: Plaintext bearer token from the Authorization header

    Returns:
        SCIMToken if valid and active, None otherwise
    """
    token_hash = _hash_token(token)
    result = await db.execute(
        select(SCIMToken).filter(SCIMToken.token_hash == token_hash, SCIMToken.is_active.is_(True))
    )
    scim_token = result.scalar_one_or_none()
    if scim_token:
        scim_token.touch()
        await db.commit()
    return scim_token


# ---------------------------------------------------------------------------
# SCIM User operations
# ---------------------------------------------------------------------------


async def list_users(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_index: int = 1,
    count: int = 100,
    filter_str: str | None = None,
) -> dict:
    """
    Return a SCIM ListResponse for Users belonging to tenant_id.

    Only accounts that are members of the tenant are included.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        start_index: 1-based offset (SCIM spec)
        count: Page size (max 200 enforced)
        filter_str: Optional SCIM filter string (only userName eq supported)

    Returns:
        SCIM ListResponse dict
    """
    count = min(count, 200)
    offset = max(start_index - 1, 0)

    # Base query — join through TenantAccountJoin to scope to tenant
    base_q = (
        select(Account)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .filter(TenantAccountJoin.tenant_id == tenant_id)
    )
    base_q = _apply_filter(base_q, filter_str)

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Paginated rows
    rows_result = await db.execute(base_q.offset(offset).limit(count))
    accounts = rows_result.scalars().all()

    return {
        "schemas": [_SCHEMA_LIST],
        "totalResults": total,
        "startIndex": start_index,
        "itemsPerPage": len(accounts),
        "Resources": [_account_to_scim(a, tenant_id) for a in accounts],
    }


async def get_user(db: AsyncSession, tenant_id: uuid.UUID, scim_user_id: str) -> dict | None:
    """
    Return a SCIM User resource by UUID, scoped to tenant_id.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        scim_user_id: String UUID of the account

    Returns:
        SCIM User dict or None if not found / not in tenant
    """
    try:
        user_uuid = uuid.UUID(scim_user_id)
    except ValueError:
        return None

    result = await db.execute(
        select(Account)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .filter(Account.id == user_uuid, TenantAccountJoin.tenant_id == tenant_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return None
    return _account_to_scim(account, tenant_id)


async def create_user(db: AsyncSession, tenant_id: uuid.UUID, scim_data: dict) -> dict:
    """
    Provision a new user for tenant_id via SCIM.

    Creates an Account (if email not already registered) and links it to the
    tenant via TenantAccountJoin.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        scim_data: Parsed SCIM User payload

    Returns:
        SCIM User dict for the created account

    Raises:
        ValueError: If userName (email) is missing or already exists in tenant
    """
    email = scim_data.get("userName", "").strip().lower()
    if not email:
        raise ValueError("userName is required")

    name = _parse_name(scim_data)
    active = scim_data.get("active", True)
    status = AccountStatus.ACTIVE if active else AccountStatus.INACTIVE

    # Check if account already exists globally
    existing_result = await db.execute(select(Account).filter(Account.email == email))
    account = existing_result.scalar_one_or_none()

    if account:
        # Check if already a member of this tenant
        membership_result = await db.execute(
            select(TenantAccountJoin).filter(
                TenantAccountJoin.tenant_id == tenant_id,
                TenantAccountJoin.account_id == account.id,
            )
        )
        if membership_result.scalar_one_or_none():
            raise ValueError(f"User {email} already exists in tenant")
    else:
        # Create new account
        account = Account(
            name=name or email.split("@")[0],
            email=email,
            status=status,
            auth_provider="scim",
        )
        db.add(account)
        await db.flush()  # populate account.id

    # Link account to tenant
    join = TenantAccountJoin(
        tenant_id=tenant_id,
        account_id=account.id,
        role=AccountRole.NORMAL,
    )
    db.add(join)
    await db.commit()
    await db.refresh(account)
    return _account_to_scim(account, tenant_id)


async def update_user(db: AsyncSession, tenant_id: uuid.UUID, scim_user_id: str, scim_data: dict) -> dict | None:
    """
    Full replace (PUT) of a SCIM User resource.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        scim_user_id: String UUID of the account
        scim_data: Parsed SCIM User payload

    Returns:
        Updated SCIM User dict, or None if not found
    """
    try:
        user_uuid = uuid.UUID(scim_user_id)
    except ValueError:
        return None

    result = await db.execute(
        select(Account)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .filter(Account.id == user_uuid, TenantAccountJoin.tenant_id == tenant_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return None

    name = _parse_name(scim_data)
    if name:
        account.name = name

    email = scim_data.get("userName", "").strip().lower()
    if email and email != account.email:
        account.email = email

    active = scim_data.get("active", True)
    account.status = AccountStatus.ACTIVE if active else AccountStatus.INACTIVE

    await db.commit()
    await db.refresh(account)
    return _account_to_scim(account, tenant_id)


async def patch_user(db: AsyncSession, tenant_id: uuid.UUID, scim_user_id: str, patch_ops: list) -> dict | None:
    """
    Partial update (PATCH) of a SCIM User resource.

    Supports the Operations array from RFC 7644 §3.5.2.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        scim_user_id: String UUID of the account
        patch_ops: List of SCIM patch operation dicts

    Returns:
        Updated SCIM User dict, or None if not found
    """
    try:
        user_uuid = uuid.UUID(scim_user_id)
    except ValueError:
        return None

    result = await db.execute(
        select(Account)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .filter(Account.id == user_uuid, TenantAccountJoin.tenant_id == tenant_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return None

    # Strict whitelist of valid SCIM User path values (lowercased for comparison).
    # Any path outside this set — including empty string or None — is rejected.
    _VALID_PATHS = {
        "username",
        "active",
        "name",
        "emails",
        "name.givenname",
        "name.familyname",
        "displayname",
        "externalid",
    }

    _SCIM_ERROR_SCHEMA = ["urn:ietf:params:scim:api:messages:2.0:Error"]

    for op in patch_ops:
        op_name = (op.get("op") or "").lower()
        raw_path = op.get("path")
        path = (raw_path or "").strip().lower()
        value = op.get("value")

        if op_name == "replace":
            if path == "":
                # replace without path — value must be a dict; validate all keys
                if not isinstance(value, dict):
                    raise ValueError("replace without path requires a dict value")
                invalid_keys = {k.lower() for k in value} - _VALID_PATHS
                if invalid_keys:
                    raise ValueError(f"Unsupported SCIM path(s) in replace value: {', '.join(sorted(invalid_keys))}")
                # Apply whitelisted fields from the value dict
                if "active" in value:
                    account.status = AccountStatus.ACTIVE if value["active"] else AccountStatus.INACTIVE
                if "userName" in value:
                    email = value["userName"].strip().lower()
                    if email:
                        account.email = email
                if "name" in value:
                    name = _parse_name(value)
                    if name:
                        account.name = name
            elif path not in _VALID_PATHS:
                raise ValueError(f"Unsupported SCIM path: {raw_path!r}")
            elif path == "active":
                if isinstance(value, bool):
                    account.status = AccountStatus.ACTIVE if value else AccountStatus.INACTIVE
                elif isinstance(value, dict) and "active" in value:
                    account.status = AccountStatus.ACTIVE if value["active"] else AccountStatus.INACTIVE
            elif path == "username":
                email = (value or "").strip().lower()
                if email:
                    account.email = email
            elif path in ("name", "name.givenname", "name.familyname"):
                if value:
                    name = _parse_name(value) if isinstance(value, dict) else str(value)
                    if name:
                        account.name = name
            elif path == "displayname":
                if value:
                    account.name = value

        elif op_name == "add":
            if path == "":
                # add without path — validate keys in value dict
                if not isinstance(value, dict):
                    raise ValueError("add without path requires a dict value")
                invalid_keys = {k.lower() for k in value} - _VALID_PATHS
                if invalid_keys:
                    raise ValueError(f"Unsupported SCIM path(s) in add value: {', '.join(sorted(invalid_keys))}")
            elif path not in _VALID_PATHS:
                raise ValueError(f"Unsupported SCIM path: {raw_path!r}")
            # Handle add operations the same as replace for our supported fields
            if isinstance(value, dict):
                if "active" in value:
                    account.status = AccountStatus.ACTIVE if value["active"] else AccountStatus.INACTIVE
                if "userName" in value:
                    email = value["userName"].strip().lower()
                    if email:
                        account.email = email

    await db.commit()
    await db.refresh(account)
    return _account_to_scim(account, tenant_id)


async def delete_user(db: AsyncSession, tenant_id: uuid.UUID, scim_user_id: str) -> bool:
    """
    Soft-delete (deactivate) a user within a tenant.

    Per SCIM spec, DELETE deactivates the user rather than destroying the record.
    The TenantAccountJoin is removed so the user no longer appears in SCIM
    listings for this tenant; the Account record itself is set to INACTIVE.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        scim_user_id: String UUID of the account

    Returns:
        True if found and deactivated, False if not found
    """
    try:
        user_uuid = uuid.UUID(scim_user_id)
    except ValueError:
        return False

    result = await db.execute(
        select(Account)
        .join(TenantAccountJoin, TenantAccountJoin.account_id == Account.id)
        .filter(Account.id == user_uuid, TenantAccountJoin.tenant_id == tenant_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return False

    # Deactivate account
    account.status = AccountStatus.INACTIVE

    # Remove from tenant membership
    join_result = await db.execute(
        select(TenantAccountJoin).filter(
            TenantAccountJoin.tenant_id == tenant_id,
            TenantAccountJoin.account_id == account.id,
        )
    )
    join = join_result.scalar_one_or_none()
    if join:
        await db.delete(join)

    # Revoke all active JWT sessions so existing tokens are immediately invalidated.
    # This must happen before commit so the account record is visible to revoke_session.
    try:
        await SessionService.revoke_session(db, account_id=account.id)
    except Exception:
        logger.warning("Failed to revoke sessions for SCIM-deprovisioned account %s", account.id, exc_info=True)

    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Token management helpers (used by the admin management API)
# ---------------------------------------------------------------------------


async def create_scim_token(
    db: AsyncSession, tenant_id: uuid.UUID, description: str | None = None
) -> tuple[str, SCIMToken]:
    """
    Create a new SCIM token for tenant_id.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        description: Optional human-readable label

    Returns:
        (plaintext_token, SCIMToken record) — store only the record; show plaintext once
    """
    plaintext, token_hash = generate_scim_token()
    token = SCIMToken(
        tenant_id=tenant_id,
        token_hash=token_hash,
        description=description,
        is_active=True,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return plaintext, token


async def list_scim_tokens(db: AsyncSession, tenant_id: uuid.UUID) -> list[SCIMToken]:
    """List all SCIM tokens for tenant_id (no plaintext)."""
    result = await db.execute(
        select(SCIMToken).filter(SCIMToken.tenant_id == tenant_id).order_by(SCIMToken.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_scim_token(db: AsyncSession, tenant_id: uuid.UUID, token_id: uuid.UUID) -> bool:
    """
    Revoke (deactivate) a SCIM token.

    Args:
        db: Async database session
        tenant_id: Tenant scope
        token_id: UUID of the SCIMToken to revoke

    Returns:
        True if found and revoked, False if not found / wrong tenant
    """
    result = await db.execute(select(SCIMToken).filter(SCIMToken.id == token_id, SCIMToken.tenant_id == tenant_id))
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.is_active = False
    await db.commit()
    return True
