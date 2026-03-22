"""
Pydantic schemas for Load Testing API endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Common Types
# ============================================================================


class LatencyConfig(BaseModel):
    """Latency simulation configuration."""

    ttft_min_ms: int = Field(default=100, ge=0, description="Min time to first token (ms)")
    ttft_max_ms: int = Field(default=500, ge=0, description="Max time to first token (ms)")
    inter_token_min_ms: int = Field(default=10, ge=0, description="Min inter-token delay (ms)")
    inter_token_max_ms: int = Field(default=50, ge=0, description="Max inter-token delay (ms)")


class ResponseConfig(BaseModel):
    """Response generation configuration."""

    min_tokens: int = Field(default=50, ge=1, description="Minimum response tokens")
    max_tokens: int = Field(default=500, ge=1, description="Maximum response tokens")
    templates: list[str] = Field(default_factory=list, description="Response templates")
    use_lorem: bool = Field(default=True, description="Use lorem ipsum if no templates")


class ErrorConfig(BaseModel):
    """Error simulation configuration."""

    rate: float = Field(default=0.01, ge=0, le=1, description="Error rate (0-1)")
    types: list[str] = Field(
        default_factory=lambda: ["rate_limit", "timeout"],
        description="Error types to simulate",
    )


class MockConfig(BaseModel):
    """Complete mock configuration."""

    latency: LatencyConfig = Field(default_factory=LatencyConfig)
    response: ResponseConfig = Field(default_factory=ResponseConfig)
    errors: ErrorConfig = Field(default_factory=ErrorConfig)
    models: dict[str, Any] = Field(
        default_factory=lambda: {
            "allowed": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "default": "gpt-4-turbo",
        }
    )


class LoadStage(BaseModel):
    """Load test stage configuration."""

    duration: str = Field(..., description="Stage duration (e.g., '30s', '1m')")
    target: int = Field(..., ge=0, description="Target VUs at end of stage")


class LoadConfig(BaseModel):
    """Load test configuration."""

    executor: str = Field(default="ramping-vus", description="K6 executor type")
    stages: list[LoadStage] = Field(
        default_factory=lambda: [
            LoadStage(duration="30s", target=10),
            LoadStage(duration="1m", target=50),
            LoadStage(duration="30s", target=0),
        ],
        description="Load stages",
    )
    max_vus: int = Field(default=100, ge=1, description="Maximum VUs")
    duration: str | None = Field(None, description="Total duration override")
    think_time_min_ms: int = Field(default=1000, ge=0, description="Min think time")
    think_time_max_ms: int = Field(default=3000, ge=0, description="Max think time")


class ThinkTimeConfig(BaseModel):
    """Think time configuration."""

    min_ms: int = Field(default=1000, ge=0, description="Minimum think time (ms)")
    max_ms: int = Field(default=3000, ge=0, description="Maximum think time (ms)")
    distribution: str = Field(
        default="uniform",
        description="Distribution: uniform, exponential, constant",
    )


# ============================================================================
# Load Test Schemas
# ============================================================================


class CreateLoadTestRequest(BaseModel):
    """Request for creating a load test."""

    name: str = Field(..., min_length=1, max_length=255, description="Test name")
    description: str | None = Field(None, description="Test description")
    target_url: str = Field(..., min_length=1, description="AI agent endpoint URL")
    target_type: str = Field(
        default="openai_compatible",
        description="Target type: openai_compatible, anthropic, google, custom",
    )
    auth_config: dict[str, Any] | None = Field(None, description="Authentication config (API key, headers)")
    request_config: dict[str, Any] = Field(default_factory=dict, description="Request configuration")
    load_config: LoadConfig = Field(default_factory=LoadConfig, description="Load configuration")
    proxy_config_id: UUID | None = Field(None, description="Link to proxy config")


class UpdateLoadTestRequest(BaseModel):
    """Request for updating a load test."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    target_url: str | None = None
    target_type: str | None = None
    auth_config: dict[str, Any] | None = None
    request_config: dict[str, Any] | None = None
    load_config: dict[str, Any] | None = None
    proxy_config_id: UUID | None = None
    status: str | None = Field(None, description="Status: draft, ready")


class LoadTestResponse(BaseModel):
    """Response for load test."""

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    target_url: str
    target_type: str
    request_config: dict[str, Any]
    load_config: dict[str, Any]
    proxy_config_id: UUID | None
    status: str
    schedule_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    last_run: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class LoadTestListResponse(BaseModel):
    """Response for listing load tests."""

    items: list[LoadTestResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Test Run Schemas
# ============================================================================


class StartTestRunRequest(BaseModel):
    """Request for starting a test run."""

    k6_options: dict[str, Any] | None = Field(None, description="K6 execution options override")


class TestRunResponse(BaseModel):
    """Response for test run."""

    id: UUID
    tenant_id: UUID
    load_test_id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    summary_metrics: dict[str, Any] | None
    error_message: str | None
    peak_vus: int | None
    total_requests: int | None
    duration_seconds: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestRunDetailResponse(TestRunResponse):
    """Detailed test run response with K6 script."""

    k6_script: str | None
    k6_options: dict[str, Any] | None
    executor_info: dict[str, Any] | None


class TestRunListResponse(BaseModel):
    """Response for listing test runs."""

    items: list[TestRunResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Test Result Schemas
# ============================================================================


class TestResultResponse(BaseModel):
    """Response for test result data point."""

    id: UUID
    timestamp: datetime
    metric_type: str
    metric_value: float
    percentile: str | None
    tags: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class MetricsSummary(BaseModel):
    """Summary metrics for a test run."""

    http_req_duration_p50: float | None = None
    http_req_duration_p95: float | None = None
    http_req_duration_p99: float | None = None
    http_req_duration_avg: float | None = None
    http_req_duration_min: float | None = None
    http_req_duration_max: float | None = None
    http_reqs: int | None = None
    http_reqs_per_sec: float | None = None
    http_req_failed: float | None = None
    vus_max: int | None = None
    data_received: int | None = None
    data_sent: int | None = None
    iterations: int | None = None
    ttft_p50: float | None = None
    ttft_p95: float | None = None
    tokens_per_sec_avg: float | None = None


class TestResultsResponse(BaseModel):
    """Response for test results with time series data."""

    test_run_id: UUID
    summary: MetricsSummary
    time_series: list[TestResultResponse]
    total_points: int


# ============================================================================
# Test Scenario Schemas
# ============================================================================


class PromptConfig(BaseModel):
    """Prompt configuration."""

    role: str = Field(default="user", description="Role: user, system, assistant")
    content: str = Field(..., description="Prompt content")
    is_template: bool = Field(default=False, description="Whether content is a template")


class VariableConfig(BaseModel):
    """Variable configuration for prompt templating."""

    type: str = Field(..., description="Type: list, random_int, random_float, uuid")
    values: list[str] | None = Field(None, description="Values for list type")
    min: float | None = Field(None, description="Min value for numeric types")
    max: float | None = Field(None, description="Max value for numeric types")


class CreateTestScenarioRequest(BaseModel):
    """Request for creating a test scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    weight: int = Field(default=1, ge=1, le=100)
    prompts: list[PromptConfig] = Field(..., min_length=1)
    think_time_config: ThinkTimeConfig | None = None
    variables: dict[str, VariableConfig] | None = None
    request_overrides: dict[str, Any] | None = None


class UpdateTestScenarioRequest(BaseModel):
    """Request for updating a test scenario."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    weight: int | None = Field(None, ge=1, le=100)
    prompts: list[PromptConfig] | None = None
    think_time_config: ThinkTimeConfig | None = None
    variables: dict[str, VariableConfig] | None = None
    request_overrides: dict[str, Any] | None = None
    display_order: int | None = None


class TestScenarioResponse(BaseModel):
    """Response for test scenario."""

    id: UUID
    load_test_id: UUID
    name: str
    description: str | None
    weight: int
    prompts: list[dict[str, Any]]
    think_time_config: dict[str, Any] | None
    variables: dict[str, Any] | None
    request_overrides: dict[str, Any] | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Proxy Config Schemas
# ============================================================================


class CreateProxyConfigRequest(BaseModel):
    """Request for creating a proxy config."""

    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(
        default="openai",
        description="Provider: openai, anthropic, google, azure_openai, custom",
    )
    mock_config: MockConfig = Field(default_factory=MockConfig)
    rate_limit: int = Field(default=100, ge=1, description="Rate limit RPS")


class UpdateProxyConfigRequest(BaseModel):
    """Request for updating a proxy config."""

    name: str | None = Field(None, min_length=1, max_length=255)
    provider: str | None = None
    mock_config: MockConfig | None = None
    rate_limit: int | None = Field(None, ge=1)
    is_active: bool | None = None


class ProxyConfigResponse(BaseModel):
    """Response for proxy config."""

    id: UUID
    tenant_id: UUID
    name: str
    provider: str
    api_key_prefix: str
    mock_config: dict[str, Any]
    rate_limit: int
    is_active: bool
    usage_count: int
    total_tokens_generated: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateProxyConfigResponse(ProxyConfigResponse):
    """Response for creating proxy config (includes full API key once)."""

    api_key: str = Field(..., description="Full API key (shown only at creation)")


class ProxyConfigListResponse(BaseModel):
    """Response for listing proxy configs."""

    items: list[ProxyConfigResponse]
    total: int


class ProxyUsageResponse(BaseModel):
    """Response for proxy usage statistics."""

    proxy_config_id: UUID
    total_requests: int
    total_tokens: int
    requests_last_hour: int
    requests_last_day: int
    error_rate: float


# ============================================================================
# Monitoring Integration Schemas
# ============================================================================


class CreateMonitoringIntegrationRequest(BaseModel):
    """Request for creating a monitoring integration."""

    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(
        ...,
        description="Provider: datadog, opentelemetry, grafana_cloud, prometheus, webhook, slack, pagerduty",
    )
    config: dict[str, Any] = Field(..., description="Provider configuration")
    export_settings: dict[str, Any] | None = Field(None, description="Export settings")


class UpdateMonitoringIntegrationRequest(BaseModel):
    """Request for updating a monitoring integration."""

    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict[str, Any] | None = None
    export_settings: dict[str, Any] | None = None
    is_active: bool | None = None


class MonitoringIntegrationResponse(BaseModel):
    """Response for monitoring integration."""

    id: UUID
    tenant_id: UUID
    name: str
    provider: str
    is_active: bool
    export_settings: dict[str, Any] | None
    last_sync_at: datetime | None
    sync_status: str | None
    sync_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitoringIntegrationListResponse(BaseModel):
    """Response for listing monitoring integrations."""

    items: list[MonitoringIntegrationResponse]
    total: int


class TestConnectionResponse(BaseModel):
    """Response for testing monitoring connection."""

    success: bool
    message: str
    details: dict[str, Any] | None = None


# ============================================================================
# Export Schemas
# ============================================================================


class ExportRequest(BaseModel):
    """Request for exporting test results."""

    format: str = Field(default="json", description="Export format: json, csv, pdf")
    include_time_series: bool = Field(default=True, description="Include time series data")
    include_k6_script: bool = Field(default=False, description="Include generated K6 script")


class ExportResponse(BaseModel):
    """Response for export request."""

    download_url: str
    expires_at: datetime
    format: str
    file_size: int


# ============================================================================
# Schedule Schemas
# ============================================================================


class ScheduleConfig(BaseModel):
    """Schedule configuration for recurring tests."""

    enabled: bool = Field(default=False)
    cron: str = Field(..., description="Cron expression")
    timezone: str = Field(default="UTC")
    max_runs: int | None = Field(None, ge=1, description="Max scheduled runs")


class ScheduleTestRequest(BaseModel):
    """Request for scheduling a test."""

    schedule_config: ScheduleConfig
