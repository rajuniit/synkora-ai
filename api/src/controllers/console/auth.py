"""
Console authentication endpoints.

Handles login, registration, token refresh, and logout.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import get_async_db
from src.middleware import get_current_account
from src.models import Account
from src.services import AuthService, SessionService
from src.services.security.password_validator import PasswordValidator
from src.utils.config_helper import get_app_base_url

logger = logging.getLogger(__name__)

# Cookie security settings — driven by the canonical APP_ENV setting, not a
# separate ENVIRONMENT variable that could be mismatched in production.
COOKIE_SECURE = settings.is_production
COOKIE_DOMAIN = settings.cookie_domain if hasattr(settings, "cookie_domain") else None

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(min_length=6)
    two_factor_token: str | None = Field(default=None, min_length=6, max_length=6)  # TOTP code
    temp_token: str | None = None  # Required when submitting two_factor_token


class RegisterRequest(BaseModel):
    """Registration request schema with strong password policy."""

    email: EmailStr
    password: str = Field(max_length=128)
    name: str = Field(min_length=1, max_length=100)
    tenant_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        is_valid, error_msg = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class RefreshRequest(BaseModel):
    """Token refresh request schema.

    refresh_token is optional — the preferred path is the HttpOnly cookie
    set by the login endpoint.  The body field is accepted as a fallback
    (e.g. mobile clients that cannot use cookies).
    """

    refresh_token: str | None = None
    tenant_id: str | None = None  # Optional tenant ID to preserve context


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Login endpoint.

    Args:
        data: Login credentials
        db: Database session

    Returns:
        Authentication tokens and user information
        If 2FA is enabled, returns requires_2fa: true and a temporary token
    """
    # Authenticate user
    try:
        account = await AuthService.authenticate(db, data.email, data.password)
    except ValueError as e:
        # SECURITY: Account is locked due to too many failed attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # SECURITY: Check if 2FA is enabled AND configured for this account
    # Only require 2FA if both the flag is set AND the secret exists
    # SECURITY FIX: Removed ENFORCE_2FA bypass - 2FA cannot be bypassed via environment variable
    two_factor_enabled = getattr(account, "two_factor_enabled", False)
    two_factor_secret = getattr(account, "two_factor_secret", None)

    if two_factor_enabled and two_factor_secret:
        # If 2FA token not provided, return partial response requiring 2FA
        if not data.two_factor_token:
            # Generate a temporary token for 2FA flow (expires in 5 minutes)
            import json
            import secrets

            temp_token = secrets.token_urlsafe(32)

            # SECURITY: Store 2FA pending tokens in Redis - no fallback
            from src.config.redis import get_redis_async

            redis_client = get_redis_async()
            if not redis_client:
                logger.warning("SECURITY: Redis unavailable for 2FA token storage")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service temporarily unavailable. Please try again later.",
                )

            # Store with 5 minute TTL
            await redis_client.setex(
                f"2fa_pending:{temp_token}",
                300,  # 5 minutes TTL
                json.dumps({"account_id": str(account.id)}),
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": False,
                    "requires_2fa": True,
                    "temp_token": temp_token,
                    "message": "Two-factor authentication required",
                },
            )
        else:
            # Verify 2FA token — requires the temp_token issued in the first step
            import json

            import pyotp

            from src.config.redis import get_redis_async

            redis_client = get_redis_async()
            if not redis_client:
                logger.warning("SECURITY: Redis unavailable for 2FA verification")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service temporarily unavailable. Please try again later.",
                )

            # Require temp_token — prevents skipping the challenge step
            if not data.temp_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="temp_token is required for two-factor authentication",
                )

            pending_key = f"2fa_pending:{data.temp_token}"
            pending_data = await redis_client.get(pending_key)
            if not pending_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Two-factor session expired or invalid. Please log in again.",
                )

            pending = json.loads(pending_data)
            if pending.get("account_id") != str(account.id):
                # Token/account mismatch — reject and invalidate token
                await redis_client.delete(pending_key)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid two-factor session.",
                )

            # Rate-limit TOTP attempts per temp_token (max 5)
            attempts_key = f"2fa_attempts:{data.temp_token}"
            attempt_count = await redis_client.incr(attempts_key)
            await redis_client.expire(attempts_key, 300)  # Expire with the session

            if attempt_count > 5:
                await redis_client.delete(pending_key)
                await redis_client.delete(attempts_key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many two-factor attempts. Please log in again.",
                )

            totp = pyotp.TOTP(two_factor_secret)
            if not totp.verify(data.two_factor_token, valid_window=1):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid two-factor authentication code"
                )

            # TOTP verified — consume the pending token (single-use)
            await redis_client.delete(pending_key)
            await redis_client.delete(attempts_key)

    # Get user's tenants
    tenants = await AuthService.get_account_tenants(db, account.id)

    # Create session with first tenant (or None if no tenants)
    tenant_id = tenants[0]["tenant_id"] if tenants else None
    session_data = await SessionService.create_session(db, account, tenant_id)

    # Build response data
    response_data = {
        "success": True,
        "data": {
            **session_data,
            "account": {
                "id": str(account.id),
                "email": account.email,
                "name": account.name,
                "status": account.status,
            },
            "tenants": tenants,
        },
        "message": "Login successful",
    }

    # Store the refresh token in an HttpOnly cookie so JS cannot read it (XSS-safe).
    # Scoped to the refresh endpoint only — the browser never sends it on normal API calls.
    # The access token is returned in the response body and kept in JS memory by the SPA.
    response = JSONResponse(content=response_data)
    response.set_cookie(
        key="refresh_token",
        value=session_data["refresh_token"],
        httponly=True,  # JS-unreachable — XSS cannot steal the refresh token
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=30 * 24 * 3600,  # 30 days — matches refresh token lifetime
        path="/console/api/auth/refresh",  # Sent only to the refresh endpoint
        domain=COOKIE_DOMAIN,
    )

    return response


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Registration endpoint.

    Args:
        data: Registration information
        db: Database session

    Returns:
        Authentication tokens and user information
    """
    try:
        # Register user
        account, tenant = await AuthService.register(
            db,
            email=data.email,
            password=data.password,
            name=data.name,
            tenant_name=data.tenant_name,
        )

        # Send verification email asynchronously using Celery
        try:
            from src.tasks.email_tasks import send_verification_email_task

            # Get base URL from request or use default
            base_url = await get_app_base_url(db, tenant.id)

            # Queue email task asynchronously
            send_verification_email_task.delay(account_id=str(account.id), base_url=base_url)
            logger.info(f"Verification email task queued for account {account.id}")
        except Exception as e:
            # Log error but don't fail registration
            logger.error(f"Failed to queue verification email: {e}")

        # Don't create session - user needs to verify email first
        # Build response without session tokens
        return {
            "success": True,
            "data": {
                "account": {
                    "id": str(account.id),
                    "email": account.email,
                    "name": account.name,
                    "status": account.status,
                },
                "tenant": {
                    "id": str(tenant.id),
                    "name": tenant.name,
                    "plan": tenant.plan,
                    "status": tenant.status,
                },
            },
            "message": "Registration successful. Please check your email to verify your account.",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/refresh")
async def refresh(request: Request, data: RefreshRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Token refresh endpoint.

    Accepts the refresh token from the HttpOnly cookie (preferred, browser clients)
    or from the request body (fallback for mobile / non-browser clients).

    Returns a new access token in the response body and rotates the refresh token
    cookie so the old one cannot be replayed.
    """
    try:
        # Cookie takes priority — JS cannot forge it (HttpOnly)
        refresh_token = request.cookies.get("refresh_token") or data.refresh_token
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is required",
            )

        tenant_id = None
        if data.tenant_id:
            import uuid

            tenant_id = uuid.UUID(data.tenant_id)

        session_data = await SessionService.refresh_session(db, refresh_token, tenant_id)

        response_data = {
            "success": True,
            "data": session_data,
            "message": "Token refreshed successfully",
        }

        # Rotate the refresh token cookie — old token is now invalid
        response = JSONResponse(content=response_data)
        response.set_cookie(
            key="refresh_token",
            value=session_data["refresh_token"],
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=30 * 24 * 3600,
            path="/console/api/auth/refresh",
            domain=COOKIE_DOMAIN,
        )

        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e


@router.post("/logout")
async def logout(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Logout endpoint.

    Args:
        current_account: Current authenticated account
        db: Database session

    Returns:
        Success message
    """
    # Revoke session
    await SessionService.revoke_session(db, current_account.id)

    # Clear the refresh token cookie
    response = JSONResponse(
        content={
            "success": True,
            "message": "Logout successful",
        }
    )
    response.delete_cookie(
        key="refresh_token",
        path="/console/api/auth/refresh",
        domain=COOKIE_DOMAIN,
    )

    return response


# Alias routes for frontend compatibility
@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(data: RegisterRequest, db: AsyncSession = Depends(get_async_db)):
    """Alias for /register endpoint."""
    return await register(data, db)


@router.post("/signin")
async def signin(data: LoginRequest, db: AsyncSession = Depends(get_async_db)):
    """Alias for /login endpoint."""
    return await login(data, db)


@router.get("/me")
async def get_current_user(
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get current user information.

    Args:
        current_account: Current authenticated account
        db: Database session

    Returns:
        User account and tenant information
    """
    import json

    from src.config.redis import get_redis_async

    cache_key = f"me:{current_account.id}"
    redis = get_redis_async()

    # Try Redis cache first (60s TTL — fresh enough for nav, fast on every page load)
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Get user's tenants
    tenants = await AuthService.get_account_tenants(db, current_account.id)

    result = {
        "success": True,
        "data": {
            "account": {
                "id": str(current_account.id),
                "email": current_account.email,
                "name": current_account.name,
                "status": current_account.status,
                "created_at": current_account.created_at.isoformat(),
            },
            "tenants": tenants,
        },
    }

    if redis:
        try:
            await redis.setex(cache_key, 60, json.dumps(result, default=str))
        except Exception:
            pass

    return result


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request model for reset password with strong password policy."""

    token: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        is_valid, error_msg = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class VerifyEmailRequest(BaseModel):
    """Request model for email verification."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Request model for resending verification email."""

    email: EmailStr


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Request a password reset email.

    Args:
        data: Forgot password request with email
        db: Database session

    Returns:
        Success message
    """
    result = await AuthService.request_password_reset(db, data.email)

    # Always return success to prevent email enumeration
    if result:
        from src.tasks.email_tasks import send_password_reset_email_task
        from src.utils.config_helper import get_app_base_url

        account, reset_token = result

        # Get base URL (tenant_id not needed; falls back to APP_BASE_URL env var)
        base_url = await get_app_base_url(db)

        # Queue password reset email asynchronously
        try:
            send_password_reset_email_task.delay(email=account.email, reset_token=reset_token, base_url=base_url)
            logger.info(f"Password reset email task queued for {account.email}")
        except Exception as e:
            logger.error(f"Failed to queue password reset email: {e}")

    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent.",
    }


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Reset password using a reset token.

    Args:
        data: Reset password request with token and new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid or expired
    """
    account = await AuthService.reset_password(db, data.token, data.new_password)

    if not account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    return {
        "success": True,
        "message": "Password has been reset successfully",
    }


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Verify email using a verification token.

    Args:
        data: Verify email request with token
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If token is invalid
    """
    account = await AuthService.verify_email(db, data.token)

    if not account:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    return {
        "success": True,
        "message": "Email has been verified successfully",
        "data": {
            "account": {
                "id": str(account.id),
                "email": account.email,
                "name": account.name,
            }
        },
    }


@router.post("/resend-verification")
async def resend_verification(data: ResendVerificationRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Resend email verification link.

    Args:
        data: Resend verification request with email
        db: Database session

    Returns:
        Success message
    """
    # Find account by email
    result = await db.execute(select(Account).filter_by(email=data.email))
    account = result.scalar_one_or_none()

    if account and account.id:
        from src.tasks.email_tasks import send_verification_email_task

        # Get base URL (tenant_id not needed; falls back to APP_BASE_URL env var)
        base_url = await get_app_base_url(db)

        # Queue verification email asynchronously
        try:
            send_verification_email_task.delay(account_id=str(account.id), base_url=base_url)
            logger.info(f"Resend verification email task queued for account {account.id}")
        except Exception as e:
            logger.error(f"Failed to queue verification email: {e}")

    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If the email exists, a verification link has been sent.",
    }
