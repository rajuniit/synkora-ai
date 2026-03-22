"""
App model for managing AI applications.

An App represents a configured AI application with specific settings,
prompts, and model configurations.
"""

import enum
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class AppMode(enum.StrEnum):
    """App execution modes."""

    COMPLETION = "COMPLETION"  # Single completion
    CHAT = "CHAT"  # Multi-turn conversation
    AGENT = "AGENT"  # Agent with tools
    WORKFLOW = "WORKFLOW"  # Workflow execution


class AppStatus(enum.StrEnum):
    """App status."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class App(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    App model representing an AI application.

    Attributes:
        tenant_id: Foreign key to tenant
        name: App name
        description: App description
        mode: App execution mode (completion, chat, agent, workflow)
        icon: App icon (emoji or URL)
        icon_background: Icon background color
        model_config: Model configuration (JSON)
        app_config: App-specific configuration (JSON)
        status: App status
        created_by: User who created the app
        updated_by: User who last updated the app
    """

    __tablename__ = "apps"

    # Foreign keys
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("accounts.id"))

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[AppMode] = mapped_column(
        Enum(AppMode, native_enum=False, length=50),
        nullable=False,
        default=AppMode.CHAT,
    )

    # Visual
    icon: Mapped[str] = mapped_column(String(255), default="🤖")
    icon_background: Mapped[str] = mapped_column(String(50), default="#6366F1")

    # Configuration
    model_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    app_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Status
    status: Mapped[AppStatus] = mapped_column(
        Enum(AppStatus, native_enum=False, length=50),
        nullable=False,
        default=AppStatus.DRAFT,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="apps")
    creator: Mapped["Account"] = relationship("Account", foreign_keys=[created_by], back_populates="created_apps")
    updater: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[updated_by], back_populates="updated_apps"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="app", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<App {self.name} ({self.mode.value})>"

    def to_dict(self, include_config: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_config: Whether to include configuration details

        Returns:
            Dictionary representation
        """
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "mode": self.mode.value,
            "icon": self.icon,
            "icon_background": self.icon_background,
            "status": self.status.value,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_config:
            data["model_config"] = self.model_config
            data["app_config"] = self.app_config

        return data

    def is_active(self) -> bool:
        """Check if app is active."""
        return self.status == AppStatus.ACTIVE and not self.deleted_at

    def can_execute(self) -> bool:
        """Check if app can be executed."""
        return self.is_active() and bool(self.model_config)
