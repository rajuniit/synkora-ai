"""
Test Run Model

Database model for storing individual load test executions.
"""

from enum import StrEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class TestRunStatus(StrEnum):
    """Test run execution status."""

    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestRun(BaseModel, TenantMixin):
    """
    Test run model for individual load test executions.

    Stores execution state, generated K6 script, and summary metrics
    for each load test run.

    Attributes:
        load_test_id: Parent load test configuration
        status: Current run status
        started_at: Run start time
        completed_at: Run completion time
        k6_script: Generated K6 script content
        k6_options: K6 execution options
        summary_metrics: Aggregated test metrics
        error_message: Error message if failed
        executor_info: Docker/K8s executor metadata
    """

    __tablename__ = "test_runs"

    load_test_id = Column(
        UUID(as_uuid=True),
        ForeignKey("load_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent load test configuration",
    )

    status = Column(
        Enum(TestRunStatus),
        nullable=False,
        default=TestRunStatus.PENDING,
        index=True,
        comment="Run status",
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Run start time",
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Run completion time",
    )

    # Generated K6 script
    k6_script = Column(
        Text,
        nullable=True,
        comment="Generated K6 JavaScript test script",
    )

    # K6 execution options
    k6_options = Column(
        JSON,
        nullable=True,
        comment="""K6 execution options:
        - env: Environment variables
        - tags: Test tags
        - thresholds: Pass/fail thresholds
        """,
    )

    # Summary metrics after test completion
    summary_metrics = Column(
        JSON,
        nullable=True,
        comment="""Summary metrics:
        - http_req_duration_p50: Median latency
        - http_req_duration_p95: 95th percentile latency
        - http_req_duration_p99: 99th percentile latency
        - http_req_duration_avg: Average latency
        - http_req_duration_min: Minimum latency
        - http_req_duration_max: Maximum latency
        - http_reqs: Total requests
        - http_reqs_per_sec: Requests per second
        - http_req_failed: Failed request rate
        - vus_max: Peak virtual users
        - data_received: Total data received
        - data_sent: Total data sent
        - iterations: Total iterations
        - ttft_p50: Time to first token median
        - ttft_p95: Time to first token p95
        - tokens_per_sec_avg: Average tokens per second
        """,
    )

    # Error message if failed
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if run failed",
    )

    # Executor metadata
    executor_info = Column(
        JSON,
        nullable=True,
        comment="""Executor metadata:
        - type: docker or kubernetes
        - container_id: Container/pod ID
        - image: Docker image used
        - node: K8s node name
        """,
    )

    # Peak VUs reached
    peak_vus = Column(
        Integer,
        nullable=True,
        comment="Peak virtual users reached during test",
    )

    # Total requests made
    total_requests = Column(
        Integer,
        nullable=True,
        comment="Total HTTP requests made",
    )

    # Relationships
    load_test = relationship("LoadTest", back_populates="test_runs", lazy="select")

    results = relationship(
        "TestResult",
        back_populates="test_run",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="TestResult.timestamp",
    )

    # Table indices
    __table_args__ = (
        Index("ix_test_runs_tenant_status", "tenant_id", "status"),
        Index("ix_test_runs_load_test_status", "load_test_id", "status"),
        Index("ix_test_runs_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        """String representation of test run."""
        return f"<TestRun(id={self.id}, load_test_id={self.load_test_id}, status='{self.status}')>"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate run duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """Check if run is currently active."""
        return self.status in (
            TestRunStatus.PENDING,
            TestRunStatus.INITIALIZING,
            TestRunStatus.RUNNING,
            TestRunStatus.STOPPING,
        )

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """Convert to dictionary with computed fields."""
        data = super().to_dict(exclude=exclude)
        data["duration_seconds"] = self.duration_seconds
        data["is_active"] = self.is_active
        return data
