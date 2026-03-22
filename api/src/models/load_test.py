"""
Load Test Model

Database model for storing AI agent load test configurations.
"""

from enum import StrEnum

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class LoadTestStatus(StrEnum):
    """Load test configuration status."""

    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"


class TargetType(StrEnum):
    """Target endpoint types for load testing."""

    # Generic endpoint types
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"

    # Legacy LLM-specific types (kept for backwards compatibility)
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


class LoadTest(BaseModel, TenantMixin):
    """
    Load test configuration model.

    Stores configurations for AI agent load tests including target URLs,
    authentication settings, load patterns, and proxy configuration.

    Attributes:
        name: Test name
        description: Test description
        target_url: AI agent endpoint URL
        target_type: Type of target API (OpenAI, Anthropic, etc.)
        auth_config: Encrypted authentication configuration
        request_config: Request payload templates
        load_config: Load configuration (VUs, duration, ramp-up)
        proxy_config_id: Optional link to LLM proxy configuration
        status: Current test status
        schedule_config: Optional scheduling configuration
    """

    __tablename__ = "load_tests"

    name = Column(String(255), nullable=False, index=True, comment="Test name")

    description = Column(Text, nullable=True, comment="Test description")

    target_url = Column(String(2048), nullable=False, comment="AI agent endpoint URL")

    target_type = Column(
        Enum(TargetType),
        nullable=False,
        default=TargetType.HTTP,
        comment="Target endpoint type (HTTP, SSE, WebSocket)",
    )

    # Encrypted authentication config (API key, headers, etc.)
    auth_config_encrypted = Column(Text, nullable=True, comment="Encrypted authentication configuration")

    # Request configuration (payload templates, variable substitution rules)
    request_config = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="""Request configuration varies by target_type:
        HTTP/SSE:
        - method: HTTP method (GET, POST, etc.)
        - content_type: Content-Type header
        - body: Request body template
        - headers: Additional headers
        - connection_timeout_ms: Connection timeout (SSE)
        - read_timeout_ms: Read timeout (SSE)
        WebSocket:
        - initial_message: Message sent after connection
        - message_template: Template for chat messages
        - connection_timeout_ms: Connection timeout
        - response_timeout_ms: Response timeout
        - headers: Connection headers
        """,
    )

    # Load configuration
    load_config = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="""Load configuration:
        - executor: ramping-vus, constant-vus, etc.
        - stages: [{ duration: '30s', target: 10 }, ...]
        - max_vus: Maximum virtual users
        - duration: Total test duration
        - think_time_min_ms: Minimum think time
        - think_time_max_ms: Maximum think time
        """,
    )

    # Optional proxy configuration for mock responses
    proxy_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Link to proxy configuration for mock responses",
    )

    status = Column(
        Enum(LoadTestStatus),
        nullable=False,
        default=LoadTestStatus.DRAFT,
        index=True,
        comment="Test status",
    )

    # Optional scheduling config for recurring tests
    schedule_config = Column(
        JSON,
        nullable=True,
        comment="""Scheduling configuration:
        - enabled: Whether scheduling is enabled
        - cron: Cron expression
        - timezone: Timezone for scheduling
        - max_runs: Maximum number of scheduled runs
        """,
    )

    # Relationships
    proxy_config = relationship("ProxyConfig", back_populates="load_tests", lazy="select")

    test_runs = relationship(
        "TestRun",
        back_populates="load_test",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="desc(TestRun.created_at)",
    )

    scenarios = relationship(
        "TestScenario",
        back_populates="load_test",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Table indices
    __table_args__ = (
        Index("ix_load_tests_tenant_status", "tenant_id", "status"),
        Index("ix_load_tests_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        """String representation of load test."""
        return f"<LoadTest(id={self.id}, name='{self.name}', status='{self.status}')>"

    def set_auth_config(self, config: dict) -> None:
        """
        Encrypt and store authentication configuration.

        Args:
            config: Authentication config dictionary
        """
        import json

        from src.services.agents.security import encrypt_value

        self.auth_config_encrypted = encrypt_value(json.dumps(config))

    def get_auth_config(self) -> dict:
        """
        Decrypt and return authentication configuration.

        Returns:
            dict: Decrypted authentication config
        """
        if not self.auth_config_encrypted:
            return {}

        import json

        from src.services.agents.security import decrypt_value

        return json.loads(decrypt_value(self.auth_config_encrypted))

    @property
    def last_run(self):
        """Get the most recent test run."""
        if self.test_runs:
            return self.test_runs[0]
        return None
