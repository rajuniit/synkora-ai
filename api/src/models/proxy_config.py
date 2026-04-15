"""
Proxy Config Model

Database model for storing LLM proxy gateway configurations.
"""

import secrets
from enum import StrEnum

from sqlalchemy import Boolean, Column, Enum, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class ProxyProvider(StrEnum):
    """Supported LLM providers for proxy."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    CUSTOM = "custom"


class ProxyConfig(BaseModel, TenantMixin):
    """
    Proxy configuration model for LLM mock endpoints.

    Stores configuration for mock LLM responses during load testing,
    enabling testing without incurring real API costs.

    Attributes:
        name: Configuration name
        provider: LLM provider type
        api_key_hash: Hashed API key for authentication
        api_key_prefix: Visible prefix of API key
        mock_config: Mock response configuration
        rate_limit: Rate limit in requests per second
        is_active: Whether configuration is active
        usage_count: Total requests served
    """

    __tablename__ = "proxy_configs"

    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Configuration name",
    )

    provider = Column(
        Enum(ProxyProvider),
        nullable=False,
        default=ProxyProvider.OPENAI,
        comment="LLM provider type",
    )

    # API key for authenticating proxy requests
    api_key_hash = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of API key",
    )

    api_key_prefix = Column(
        String(16),
        nullable=False,
        comment="Visible prefix of API key (e.g., 'sk-proxy-')",
    )

    # Mock response configuration
    mock_config = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="""Mock response configuration:
        - latency:
            - ttft_min_ms: Min time to first token (100)
            - ttft_max_ms: Max time to first token (500)
            - inter_token_min_ms: Min inter-token delay (10)
            - inter_token_max_ms: Max inter-token delay (50)
        - response:
            - min_tokens: Minimum response tokens (50)
            - max_tokens: Maximum response tokens (500)
            - templates: List of response templates
            - use_lorem: Use lorem ipsum if no templates
        - errors:
            - rate: Error rate (0.01 = 1%)
            - types: ["rate_limit", "timeout", "server_error"]
        - models:
            - allowed: List of allowed model names
            - default: Default model if not specified
        """,
    )

    # Rate limiting
    rate_limit = Column(
        Integer,
        nullable=False,
        default=100,
        comment="Rate limit in requests per second",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether configuration is active",
    )

    # Usage tracking
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total requests served by this proxy",
    )

    total_tokens_generated = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total mock tokens generated",
    )

    # Relationships
    load_tests = relationship("LoadTest", back_populates="proxy_config", lazy="select")

    # Table indices
    __table_args__ = (
        Index("ix_proxy_configs_tenant_active", "tenant_id", "is_active"),
        Index("ix_proxy_configs_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        """String representation of proxy config."""
        return f"<ProxyConfig(id={self.id}, name='{self.name}', provider='{self.provider}')>"

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """
        Generate a new API key with prefix and hash.

        Returns:
            tuple: (full_key, prefix, hash)
        """
        import hashlib

        # Generate random key
        random_part = secrets.token_urlsafe(32)
        prefix = "sk-proxy-"
        full_key = f"{prefix}{random_part}"

        # Hash the key
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        return full_key, prefix, key_hash

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for comparison.

        Args:
            api_key: The API key to hash

        Returns:
            str: SHA-256 hash of the key
        """
        import hashlib

        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> bool:
        """
        Verify an API key matches this configuration.

        Args:
            api_key: The API key to verify

        Returns:
            bool: True if key matches
        """
        return self.api_key_hash == self.hash_api_key(api_key)

    def increment_usage(self, tokens: int = 0) -> None:
        """
        Increment usage counters.

        Args:
            tokens: Number of tokens generated
        """
        self.usage_count += 1
        self.total_tokens_generated += tokens

    @property
    def default_mock_config(self) -> dict:
        """Get default mock configuration."""
        return {
            "latency": {
                "ttft_min_ms": 100,
                "ttft_max_ms": 500,
                "inter_token_min_ms": 10,
                "inter_token_max_ms": 50,
            },
            "response": {
                "min_tokens": 50,
                "max_tokens": 500,
                "templates": [],
                "use_lorem": True,
            },
            "errors": {
                "rate": 0.01,
                "types": ["rate_limit", "timeout"],
            },
            "models": {
                "allowed": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"],
                "default": "gpt-4-turbo",
            },
        }
