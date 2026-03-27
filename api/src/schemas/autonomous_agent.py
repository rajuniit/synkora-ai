"""
Pydantic schemas for autonomous agent configuration and run history.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.services.scheduler.cron_validator import CronValidator

# Human-friendly schedule aliases
_SCHEDULE_ALIASES: dict[str, dict] = {
    "5min": {"interval_seconds": 300, "schedule_type": "interval"},
    "15min": {"interval_seconds": 900, "schedule_type": "interval"},
    "30min": {"interval_seconds": 1800, "schedule_type": "interval"},
    "hourly": {"interval_seconds": 3600, "schedule_type": "interval"},
    "daily": {"cron_expression": "0 9 * * *", "schedule_type": "cron"},
    "weekly": {"cron_expression": "0 9 * * 1", "schedule_type": "cron"},
}


def parse_schedule(schedule: str) -> dict:
    """
    Convert a human-friendly schedule string or raw cron expression into
    the dict consumed by ScheduledTask columns.

    Returns a dict with keys: schedule_type, cron_expression?, interval_seconds?
    Raises ValueError for invalid inputs.
    """
    if schedule in _SCHEDULE_ALIASES:
        return _SCHEDULE_ALIASES[schedule]

    # Treat as a raw cron expression
    result = CronValidator.validate(schedule)
    if not result["is_valid"]:
        raise ValueError(
            f"Invalid schedule '{schedule}'. Use one of {list(_SCHEDULE_ALIASES)} "
            f"or a valid 5-part cron expression (e.g. '0 */4 * * *')."
        )
    return {"cron_expression": schedule, "schedule_type": "cron"}


class AutonomousConfigCreate(BaseModel):
    """Request body for enabling autonomous mode on an agent."""

    goal: str = Field(..., min_length=10, description="What the agent should do on every run")
    schedule: str = Field(
        ...,
        description="Schedule alias (5min/15min/30min/hourly/daily/weekly) or raw cron expression",
    )
    max_steps: int = Field(20, ge=1, le=100, description="Maximum tool-call budget per run")

    # Human-in-the-loop approval settings
    require_approval: bool = Field(False, description="Gate action tools behind human approval")
    approval_mode: Literal["smart", "explicit"] = Field(
        "smart",
        description=(
            "smart = gate all tools tagged tool_category=action; "
            "explicit = only gate tools listed in require_approval_tools"
        ),
    )
    require_approval_tools: list[str] = Field(
        default_factory=list,
        description="Tool names to gate (only for explicit mode)",
    )
    approval_channel: Literal["slack", "whatsapp", "whatsapp_web", "chat"] | None = Field(
        None,
        description="Channel to send approval notifications",
    )
    approval_channel_config: dict = Field(
        default_factory=dict,
        description=(
            "Channel-specific routing: "
            "slack={'channel_id':'C123'}, "
            "whatsapp={'bot_id':'uuid','to_phone':'+1...'}, "
            "whatsapp_web={'session_id':'wa-xyz','to_phone':'+1...'}, "
            "chat={} (uses autonomous_conversation_id automatically)"
        ),
    )
    approval_timeout_minutes: int = Field(60, ge=5, le=1440, description="Minutes before approval expires")

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        parse_schedule(v)  # raises on invalid
        return v


class AutonomousConfigUpdate(BaseModel):
    """Request body for patching an existing autonomous configuration."""

    goal: str | None = Field(None, min_length=10)
    schedule: str | None = None
    max_steps: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None

    # Human-in-the-loop approval settings (all optional for PATCH)
    require_approval: bool | None = None
    approval_mode: Literal["smart", "explicit"] | None = None
    require_approval_tools: list[str] | None = None
    approval_channel: Literal["slack", "whatsapp", "whatsapp_web", "chat"] | None = None
    approval_channel_config: dict | None = None
    approval_timeout_minutes: int | None = Field(None, ge=5, le=1440)

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v: str | None) -> str | None:
        if v is not None:
            parse_schedule(v)
        return v


class AutonomousRunSchema(BaseModel):
    """Serialised TaskExecution record for the UI."""

    id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    execution_time_seconds: float | None = None
    error_message: str | None = None
    output_preview: str | None = None  # first 300 chars of result["response_preview"]


class AutonomousMemoryMessageSchema(BaseModel):
    """A single message from the autonomous memory conversation."""

    id: UUID
    role: str
    content: str
    created_at: datetime


class AutonomousStatusSchema(BaseModel):
    """Full status response returned by GET /agents/{name}/autonomous."""

    enabled: bool
    task_id: UUID | None = None
    goal: str | None = None
    schedule: str | None = None
    schedule_type: str | None = None
    max_steps: int = 20
    is_active: bool = False
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    recent_runs: list[AutonomousRunSchema] = []

    # HITL approval settings
    require_approval: bool = False
    approval_mode: str = "smart"
    require_approval_tools: list[str] = []
    approval_channel: str | None = None
    approval_channel_config: dict = {}
    approval_timeout_minutes: int = 60


class ApprovalRequestSchema(BaseModel):
    """Serialised AgentApprovalRequest for the dashboard UI."""

    id: UUID
    task_id: UUID
    agent_name: str
    tool_name: str
    tool_args: dict
    status: str
    notification_channel: str
    expires_at: datetime
    created_at: datetime


class ApprovalRespondBody(BaseModel):
    """Request body for POST /autonomous/approvals/{id}/respond."""

    decision: Literal["approved", "rejected", "feedback"]
    feedback_text: str | None = None
