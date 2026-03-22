"""
Test Result Model

Database model for storing granular load test metric data points.
"""

from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class MetricType(StrEnum):
    """Types of metrics captured during load tests."""

    # HTTP request metrics
    HTTP_REQ_DURATION = "http_req_duration"
    HTTP_REQ_BLOCKED = "http_req_blocked"
    HTTP_REQ_CONNECTING = "http_req_connecting"
    HTTP_REQ_TLS_HANDSHAKING = "http_req_tls_handshaking"
    HTTP_REQ_SENDING = "http_req_sending"
    HTTP_REQ_WAITING = "http_req_waiting"
    HTTP_REQ_RECEIVING = "http_req_receiving"
    HTTP_REQ_FAILED = "http_req_failed"
    HTTP_REQS = "http_reqs"

    # Virtual users
    VUS = "vus"
    VUS_MAX = "vus_max"

    # Data transfer
    DATA_RECEIVED = "data_received"
    DATA_SENT = "data_sent"

    # Iterations
    ITERATIONS = "iterations"
    ITERATION_DURATION = "iteration_duration"

    # Custom LLM metrics
    TTFT = "ttft"  # Time to first token
    TOKENS_PER_SEC = "tokens_per_sec"
    TOTAL_TOKENS = "total_tokens"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"

    # Error metrics
    ERRORS = "errors"
    ERROR_RATE = "error_rate"

    # Streaming metrics
    STREAM_CHUNKS = "stream_chunks"
    STREAM_DURATION = "stream_duration"


class PercentileType(StrEnum):
    """Percentile types for metric aggregation."""

    P50 = "p50"
    P75 = "p75"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    RATE = "rate"


class TestResult(BaseModel):
    """
    Test result model for storing granular metric data points.

    Captures time-series metric data during load test execution,
    enabling real-time visualization and post-test analysis.

    Attributes:
        test_run_id: Parent test run
        timestamp: Data point timestamp
        metric_type: Type of metric
        metric_value: Metric value
        percentile: Percentile type if aggregated
        tags: Additional metric tags
    """

    __tablename__ = "test_results"

    test_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent test run",
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Data point timestamp",
    )

    metric_type = Column(
        Enum(MetricType),
        nullable=False,
        index=True,
        comment="Type of metric",
    )

    metric_value = Column(
        Float,
        nullable=False,
        comment="Metric value",
    )

    percentile = Column(
        Enum(PercentileType),
        nullable=True,
        comment="Percentile type if this is an aggregated value",
    )

    # Additional tags for grouping/filtering
    tags = Column(
        JSON,
        nullable=True,
        comment="""Additional metric tags:
        - scenario: Scenario name
        - status_code: HTTP status code
        - url: Request URL
        - method: HTTP method
        - error_type: Type of error if any
        """,
    )

    # Relationships
    test_run = relationship("TestRun", back_populates="results", lazy="select")

    # Table indices for efficient querying
    __table_args__ = (
        Index("ix_test_results_run_timestamp", "test_run_id", "timestamp"),
        Index("ix_test_results_run_metric", "test_run_id", "metric_type"),
        Index("ix_test_results_run_metric_time", "test_run_id", "metric_type", "timestamp"),
    )

    def __repr__(self) -> str:
        """String representation of test result."""
        return f"<TestResult(id={self.id}, metric={self.metric_type.value}, value={self.metric_value})>"
