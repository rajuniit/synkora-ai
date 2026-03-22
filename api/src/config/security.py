"""Security configuration."""

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


def get_encryption_key() -> str:
    """Get the encryption key from environment variables."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not set")
    return key


class SecurityConfig(BaseSettings):
    """Security configuration settings."""

    secret_key: str = Field(
        ...,
        description=(
            "Secret key used for session signing and CSRF protection. "
            'Must be a long random string. Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        ),
    )

    jwt_secret_key: str = Field(
        ...,
        description=(
            "Secret key used exclusively for signing JWT access and refresh tokens. "
            "Separate from secret_key so token signing keys can be rotated independently. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        ),
    )

    jwt_access_token_expires: int = Field(
        default=3600,
        description="Access token expiration in seconds (default: 1 hour)",
    )

    jwt_refresh_token_expires: int = Field(
        default=2592000,
        description="Refresh token expiration in seconds (default: 30 days)",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm (HS256 recommended for single-service; RS256 for multi-service)",
    )

    jwt_issuer: str = Field(
        default="synkora-api",
        description=(
            "JWT 'iss' (issuer) claim. Override when running multiple isolated instances "
            "or integrating with external JWT validators."
        ),
    )

    jwt_audience: str = Field(
        default="synkora-app",
        description=(
            "JWT 'aud' (audience) claim. Override to match your deployment. "
            "Must match between the API that issues tokens and any service that validates them."
        ),
    )

    cookie_domain: str | None = Field(
        default=None,
        description=(
            "Domain attribute for auth cookies. None = current domain only (recommended). "
            "Set to '.example.com' (leading dot) to share cookies across subdomains."
        ),
    )

    encryption_key: str = Field(
        ...,
        description=(
            "Fernet encryption key for encrypting sensitive data at rest (OAuth tokens, API keys). "
            "Must be a URL-safe base64-encoded 32-byte key. "
            'Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        ),
    )


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""

    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting",
    )

    rate_limit_per_minute: int = Field(
        default=60,
        description="Requests per minute",
    )

    rate_limit_per_hour: int = Field(
        default=1000,
        description="Requests per hour",
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log format",
    )
