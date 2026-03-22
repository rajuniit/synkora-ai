"""add load testing tables

Revision ID: add_load_testing_tables
Revises: cc30e80dc089
Create Date: 2026-03-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_load_testing_tables"
down_revision = "cc30e80dc089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create proxy_configs table first (referenced by load_tests)
    op.create_table(
        "proxy_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider type: openai, anthropic, google, azure_openai, custom",
        ),
        sa.Column("api_key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("api_key_prefix", sa.String(16), nullable=False),
        sa.Column(
            "mock_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
            comment="Mock response configuration (latency, response, errors)",
        ),
        sa.Column("rate_limit", sa.Integer(), nullable=False, default=100),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, default=0),
        sa.Column("total_tokens_generated", sa.Integer(), nullable=False, default=0),
    )

    op.create_index("ix_proxy_configs_api_key_hash", "proxy_configs", ["api_key_hash"])
    op.create_index("ix_proxy_configs_tenant_active", "proxy_configs", ["tenant_id", "is_active"])
    op.create_index("ix_proxy_configs_tenant_name", "proxy_configs", ["tenant_id", "name"])

    # Create load_tests table
    op.create_table(
        "load_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_url", sa.String(2048), nullable=False),
        sa.Column(
            "target_type",
            sa.String(50),
            nullable=False,
            comment="Target type: openai_compatible, anthropic, google, custom",
        ),
        sa.Column(
            "auth_config_encrypted",
            sa.Text(),
            nullable=True,
            comment="Encrypted authentication configuration",
        ),
        sa.Column(
            "request_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
            comment="Request configuration (model, messages, temperature, etc.)",
        ),
        sa.Column(
            "load_config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
            comment="Load configuration (VUs, duration, stages, etc.)",
        ),
        sa.Column(
            "proxy_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("proxy_configs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            default="draft",
            comment="Status: draft, ready, running, paused",
        ),
        sa.Column(
            "schedule_config",
            postgresql.JSONB(),
            nullable=True,
            comment="Scheduling configuration (cron, timezone, etc.)",
        ),
    )

    op.create_index("ix_load_tests_name", "load_tests", ["name"])
    op.create_index("ix_load_tests_status", "load_tests", ["status"])
    op.create_index("ix_load_tests_tenant_status", "load_tests", ["tenant_id", "status"])
    op.create_index("ix_load_tests_tenant_name", "load_tests", ["tenant_id", "name"])
    op.create_index("ix_load_tests_proxy_config_id", "load_tests", ["proxy_config_id"])

    # Create test_runs table
    op.create_table(
        "test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "load_test_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("load_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            default="pending",
            comment="Status: pending, initializing, running, stopping, completed, failed, cancelled",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("k6_script", sa.Text(), nullable=True, comment="Generated K6 test script"),
        sa.Column(
            "k6_options",
            postgresql.JSONB(),
            nullable=True,
            comment="K6 execution options",
        ),
        sa.Column(
            "summary_metrics",
            postgresql.JSONB(),
            nullable=True,
            comment="Summary metrics (p95, p99, RPS, error rate, etc.)",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "executor_info",
            postgresql.JSONB(),
            nullable=True,
            comment="Executor metadata (docker/k8s info)",
        ),
        sa.Column("peak_vus", sa.Integer(), nullable=True),
        sa.Column("total_requests", sa.Integer(), nullable=True),
    )

    op.create_index("ix_test_runs_load_test_id", "test_runs", ["load_test_id"])
    op.create_index("ix_test_runs_status", "test_runs", ["status"])
    op.create_index("ix_test_runs_tenant_status", "test_runs", ["tenant_id", "status"])
    op.create_index("ix_test_runs_load_test_status", "test_runs", ["load_test_id", "status"])
    op.create_index("ix_test_runs_started_at", "test_runs", ["started_at"])

    # Create test_results table
    op.create_table(
        "test_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "test_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("test_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metric_type",
            sa.String(50),
            nullable=False,
            comment="Metric type: http_req_duration, vus, ttft, etc.",
        ),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column(
            "percentile",
            sa.String(20),
            nullable=True,
            comment="Percentile type: p50, p95, p99, avg, min, max, count, rate",
        ),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=True,
            comment="Additional metric tags (scenario, status_code, etc.)",
        ),
    )

    op.create_index("ix_test_results_test_run_id", "test_results", ["test_run_id"])
    op.create_index("ix_test_results_timestamp", "test_results", ["timestamp"])
    op.create_index("ix_test_results_metric_type", "test_results", ["metric_type"])
    op.create_index("ix_test_results_run_timestamp", "test_results", ["test_run_id", "timestamp"])
    op.create_index("ix_test_results_run_metric", "test_results", ["test_run_id", "metric_type"])
    op.create_index(
        "ix_test_results_run_metric_time",
        "test_results",
        ["test_run_id", "metric_type", "timestamp"],
    )

    # Create test_scenarios table
    op.create_table(
        "test_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "load_test_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("load_tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, default=1),
        sa.Column(
            "prompts",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
            comment="Array of prompt configurations",
        ),
        sa.Column(
            "think_time_config",
            postgresql.JSONB(),
            nullable=True,
            comment="Think time configuration",
        ),
        sa.Column(
            "variables",
            postgresql.JSONB(),
            nullable=True,
            comment="Variable definitions for prompt templating",
        ),
        sa.Column(
            "request_overrides",
            postgresql.JSONB(),
            nullable=True,
            comment="Request configuration overrides",
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, default=0),
    )

    op.create_index("ix_test_scenarios_load_test_id", "test_scenarios", ["load_test_id"])
    op.create_index("ix_test_scenarios_name", "test_scenarios", ["name"])
    op.create_index(
        "ix_test_scenarios_load_test_order", "test_scenarios", ["load_test_id", "display_order"]
    )

    # Create monitoring_integrations table
    op.create_table(
        "monitoring_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider: datadog, opentelemetry, grafana_cloud, prometheus, webhook, slack, pagerduty",
        ),
        sa.Column(
            "config_data_encrypted",
            sa.Text(),
            nullable=True,
            comment="Encrypted provider configuration",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "export_settings",
            postgresql.JSONB(),
            nullable=True,
            comment="Export settings (auto_export, metric_prefix, etc.)",
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(50), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
    )

    op.create_index("ix_monitoring_integrations_name", "monitoring_integrations", ["name"])
    op.create_index("ix_monitoring_integrations_provider", "monitoring_integrations", ["provider"])
    op.create_index(
        "ix_monitoring_integrations_tenant_active",
        "monitoring_integrations",
        ["tenant_id", "is_active"],
    )
    op.create_index(
        "ix_monitoring_integrations_tenant_provider",
        "monitoring_integrations",
        ["tenant_id", "provider"],
    )


def downgrade() -> None:
    # Drop monitoring_integrations
    op.drop_index("ix_monitoring_integrations_tenant_provider", table_name="monitoring_integrations")
    op.drop_index("ix_monitoring_integrations_tenant_active", table_name="monitoring_integrations")
    op.drop_index("ix_monitoring_integrations_provider", table_name="monitoring_integrations")
    op.drop_index("ix_monitoring_integrations_name", table_name="monitoring_integrations")
    op.drop_table("monitoring_integrations")

    # Drop test_scenarios
    op.drop_index("ix_test_scenarios_load_test_order", table_name="test_scenarios")
    op.drop_index("ix_test_scenarios_name", table_name="test_scenarios")
    op.drop_index("ix_test_scenarios_load_test_id", table_name="test_scenarios")
    op.drop_table("test_scenarios")

    # Drop test_results
    op.drop_index("ix_test_results_run_metric_time", table_name="test_results")
    op.drop_index("ix_test_results_run_metric", table_name="test_results")
    op.drop_index("ix_test_results_run_timestamp", table_name="test_results")
    op.drop_index("ix_test_results_metric_type", table_name="test_results")
    op.drop_index("ix_test_results_timestamp", table_name="test_results")
    op.drop_index("ix_test_results_test_run_id", table_name="test_results")
    op.drop_table("test_results")

    # Drop test_runs
    op.drop_index("ix_test_runs_started_at", table_name="test_runs")
    op.drop_index("ix_test_runs_load_test_status", table_name="test_runs")
    op.drop_index("ix_test_runs_tenant_status", table_name="test_runs")
    op.drop_index("ix_test_runs_status", table_name="test_runs")
    op.drop_index("ix_test_runs_load_test_id", table_name="test_runs")
    op.drop_table("test_runs")

    # Drop load_tests
    op.drop_index("ix_load_tests_proxy_config_id", table_name="load_tests")
    op.drop_index("ix_load_tests_tenant_name", table_name="load_tests")
    op.drop_index("ix_load_tests_tenant_status", table_name="load_tests")
    op.drop_index("ix_load_tests_status", table_name="load_tests")
    op.drop_index("ix_load_tests_name", table_name="load_tests")
    op.drop_table("load_tests")

    # Drop proxy_configs
    op.drop_index("ix_proxy_configs_tenant_name", table_name="proxy_configs")
    op.drop_index("ix_proxy_configs_tenant_active", table_name="proxy_configs")
    op.drop_index("ix_proxy_configs_api_key_hash", table_name="proxy_configs")
    op.drop_table("proxy_configs")
