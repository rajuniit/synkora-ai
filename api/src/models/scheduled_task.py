"""Scheduled Task Models"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class TaskStatus(StrEnum):
    """Task execution status enum"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"
    CANCELLED = "cancelled"


class ScheduledTask(Base):
    """Scheduled Task Model"""

    __tablename__ = "scheduled_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False, index=True)  # 'database_query', 'chart_generation', 'report'
    schedule_type = Column(String(20), nullable=False)  # 'cron', 'interval'
    cron_expression = Column(String(100), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="scheduled_tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    notifications = relationship("TaskNotification", back_populates="task", cascade="all, delete-orphan")

    @property
    def database_connection_id(self) -> int | None:
        """Get database connection ID from config"""
        return self.config.get("database_connection_id")

    @property
    def query(self) -> str | None:
        """Get query from config"""
        return self.config.get("query")

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "config": self.config,
            "is_active": self.is_active,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by),
        }


class TaskExecution(Base):
    """Task Execution Model"""

    __tablename__ = "task_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(String(20), nullable=False, index=True)  # 'pending', 'running', 'success', 'failed', 'cancelled'
    celery_task_id = Column(String(36), nullable=True, index=True)  # Celery task UUID for revoke
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    task = relationship("ScheduledTask", back_populates="executions")

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time_seconds": self.execution_time_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TaskNotification(Base):
    """Task Notification Model"""

    __tablename__ = "task_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type = Column(String(20), nullable=False, index=True)  # 'email', 'slack', 'webhook'
    config = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    task = relationship("ScheduledTask", back_populates="notifications")

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "notification_type": self.notification_type,
            "config": self.config,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
