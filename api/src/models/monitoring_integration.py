"""
Monitoring Integration Model

Database model for storing external monitoring platform configurations.
"""

from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON

from src.models.base import BaseModel, TenantMixin


class MonitoringProvider(StrEnum):
    """Supported monitoring platforms."""

    DATADOG = "datadog"
    OPENTELEMETRY = "opentelemetry"  # OTLP
    GRAFANA_CLOUD = "grafana_cloud"
    PROMETHEUS = "prometheus"
    WEBHOOK = "webhook"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"


class MonitoringIntegration(BaseModel, TenantMixin):
    """
    Monitoring integration model for external platform connections.

    Stores configuration for exporting load test metrics to
    external monitoring platforms like DataDog, Grafana, etc.

    Attributes:
        name: Integration name
        provider: Monitoring platform type
        config_data_encrypted: Encrypted provider configuration
        is_active: Whether integration is active
        last_sync_at: Last successful export
        sync_status: Status of last sync
        sync_error: Error message from last failed sync
    """

    __tablename__ = "monitoring_integrations"

    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Integration name",
    )

    provider = Column(
        Enum(MonitoringProvider),
        nullable=False,
        index=True,
        comment="Monitoring platform type",
    )

    # Encrypted provider configuration
    config_data_encrypted = Column(
        Text,
        nullable=True,
        comment="Encrypted provider configuration (API keys, endpoints, etc.)",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether integration is active",
    )

    # Export settings
    export_settings = Column(
        JSON,
        nullable=True,
        comment="""Export settings:
        - auto_export: Export after each test run
        - metric_prefix: Prefix for metric names
        - include_tags: Tags to include with metrics
        - aggregation_interval_sec: Metric aggregation interval
        """,
    )

    # Sync status tracking
    last_sync_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful export",
    )

    sync_status = Column(
        String(50),
        nullable=True,
        comment="Status of last sync: success, failed, pending",
    )

    sync_error = Column(
        Text,
        nullable=True,
        comment="Error message from last failed sync",
    )

    # Table indices
    __table_args__ = (
        Index("ix_monitoring_integrations_tenant_active", "tenant_id", "is_active"),
        Index("ix_monitoring_integrations_tenant_provider", "tenant_id", "provider"),
    )

    def __repr__(self) -> str:
        """String representation of monitoring integration."""
        return f"<MonitoringIntegration(id={self.id}, name='{self.name}', provider='{self.provider}')>"

    def set_config(self, config: dict) -> None:
        """
        Encrypt and store provider configuration.

        Args:
            config: Provider configuration dictionary
        """
        import json

        from src.services.agents.security import encrypt_value

        self.config_data_encrypted = encrypt_value(json.dumps(config))

    def get_config(self) -> dict:
        """
        Decrypt and return provider configuration.

        Returns:
            dict: Decrypted provider configuration
        """
        if not self.config_data_encrypted:
            return {}

        import json

        from src.services.agents.security import decrypt_value

        return json.loads(decrypt_value(self.config_data_encrypted))

    @staticmethod
    def get_config_schema(provider: MonitoringProvider) -> dict:
        """
        Get configuration schema for a provider.

        Args:
            provider: Monitoring provider type

        Returns:
            dict: Configuration schema with required fields
        """
        schemas = {
            MonitoringProvider.DATADOG: {
                "required": ["api_key", "app_key"],
                "optional": ["site", "metric_prefix", "tags"],
                "fields": {
                    "api_key": {"type": "string", "description": "DataDog API key"},
                    "app_key": {"type": "string", "description": "DataDog application key"},
                    "site": {
                        "type": "string",
                        "description": "DataDog site (datadoghq.com, datadoghq.eu, etc.)",
                        "default": "datadoghq.com",
                    },
                    "metric_prefix": {
                        "type": "string",
                        "description": "Prefix for all metric names",
                        "default": "synkora.loadtest",
                    },
                    "tags": {
                        "type": "array",
                        "description": "Default tags for all metrics",
                        "default": [],
                    },
                },
            },
            MonitoringProvider.OPENTELEMETRY: {
                "required": ["endpoint"],
                "optional": ["headers", "protocol", "resource_attributes"],
                "fields": {
                    "endpoint": {"type": "string", "description": "OTLP endpoint URL"},
                    "headers": {"type": "object", "description": "HTTP headers for authentication"},
                    "protocol": {
                        "type": "string",
                        "description": "Protocol: grpc or http",
                        "default": "http",
                    },
                    "resource_attributes": {
                        "type": "object",
                        "description": "Resource attributes for OTLP",
                        "default": {},
                    },
                },
            },
            MonitoringProvider.GRAFANA_CLOUD: {
                "required": ["prometheus_url", "username", "api_key"],
                "optional": ["metric_prefix"],
                "fields": {
                    "prometheus_url": {"type": "string", "description": "Grafana Cloud Prometheus URL"},
                    "username": {"type": "string", "description": "Grafana Cloud username (instance ID)"},
                    "api_key": {"type": "string", "description": "Grafana Cloud API key"},
                    "metric_prefix": {
                        "type": "string",
                        "description": "Prefix for metric names",
                        "default": "synkora_loadtest",
                    },
                },
            },
            MonitoringProvider.PROMETHEUS: {
                "required": ["pushgateway_url"],
                "optional": ["job_name", "basic_auth"],
                "fields": {
                    "pushgateway_url": {"type": "string", "description": "Prometheus Pushgateway URL"},
                    "job_name": {
                        "type": "string",
                        "description": "Job name for metrics",
                        "default": "synkora_loadtest",
                    },
                    "basic_auth": {
                        "type": "object",
                        "description": "Basic auth credentials",
                        "properties": {"username": {"type": "string"}, "password": {"type": "string"}},
                    },
                },
            },
            MonitoringProvider.WEBHOOK: {
                "required": ["url"],
                "optional": ["method", "headers", "batch_size"],
                "fields": {
                    "url": {"type": "string", "description": "Webhook URL"},
                    "method": {"type": "string", "description": "HTTP method", "default": "POST"},
                    "headers": {"type": "object", "description": "HTTP headers", "default": {}},
                    "batch_size": {
                        "type": "integer",
                        "description": "Number of metrics per batch",
                        "default": 100,
                    },
                },
            },
            MonitoringProvider.SLACK: {
                "required": ["webhook_url"],
                "optional": ["channel", "notify_on"],
                "fields": {
                    "webhook_url": {"type": "string", "description": "Slack webhook URL"},
                    "channel": {"type": "string", "description": "Override channel"},
                    "notify_on": {
                        "type": "array",
                        "description": "Events to notify on",
                        "default": ["test_complete", "test_failed"],
                    },
                },
            },
            MonitoringProvider.PAGERDUTY: {
                "required": ["routing_key"],
                "optional": ["severity", "component"],
                "fields": {
                    "routing_key": {"type": "string", "description": "PagerDuty routing key"},
                    "severity": {
                        "type": "string",
                        "description": "Default severity",
                        "default": "warning",
                    },
                    "component": {
                        "type": "string",
                        "description": "Component name",
                        "default": "load-testing",
                    },
                },
            },
        }

        return schemas.get(provider, {"required": [], "optional": [], "fields": {}})
