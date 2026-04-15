"""
AgentCompute model — assigns an isolated compute target to an agent.

When an AgentCompute record exists for an agent, all command and
file-system tool calls are routed to that compute target instead of
the local platform workspace.
"""

from enum import StrEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class ComputeType(StrEnum):
    """Type of compute target."""

    LOCAL = "local"
    REMOTE_SERVER = "remote_server"
    PLATFORM_MANAGED = "platform_managed"


class ComputeStatus(StrEnum):
    """Operational status of the compute assignment."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AgentCompute(BaseModel, TenantMixin):
    """
    Compute target assigned to an agent.

    When compute_type is LOCAL (default), the existing workspace-mount
    behaviour is preserved and this record is optional.

    When compute_type is REMOTE_SERVER, command and file-system tools
    are executed on the remote host over SSH instead of locally.
    """

    __tablename__ = "agent_computes"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Agent this compute is assigned to (1:1)",
    )

    compute_type = Column(
        String(50),
        nullable=False,
        default=ComputeType.LOCAL,
        index=True,
        comment="Type of compute target: local | remote_server | platform_managed",
    )

    status = Column(
        String(50),
        nullable=False,
        default=ComputeStatus.ACTIVE,
        index=True,
        comment="Operational status: active | inactive | error",
    )

    # --- Remote server configuration ---

    remote_host = Column(
        Text,
        nullable=True,
        comment="Hostname or IP of the remote compute target",
    )

    remote_port = Column(
        Integer,
        nullable=True,
        default=22,
        comment="SSH port (default 22)",
    )

    remote_user = Column(
        Text,
        nullable=True,
        default="root",
        comment="SSH username",
    )

    remote_auth_type = Column(
        String(50),
        nullable=True,
        default="key",
        comment="SSH authentication method: key | password",
    )

    remote_credentials_encrypted = Column(
        Text,
        nullable=True,
        comment="Fernet-encrypted SSH private key (PEM) or password",
    )

    remote_base_path = Column(
        Text,
        nullable=True,
        default="/tmp/agent_workspace",
        comment="Working directory on the remote host",
    )

    # --- Resource and execution limits ---

    timeout_seconds = Column(
        Integer,
        nullable=False,
        default=300,
        comment="Per-command timeout in seconds",
    )

    max_output_chars = Column(
        Integer,
        nullable=False,
        default=8000,
        comment="Max characters of stdout returned per command",
    )

    # --- Command allowlist override ---
    # Null = use the global SAFE_COMMANDS default from command_tools.py.
    # Provide a JSON array of command names to restrict further,
    # e.g. ["git", "ls", "cat", "grep"].
    allowed_commands_override = Column(
        JSON,
        nullable=True,
        comment="JSON array of allowed command names; null = use global default",
    )

    # --- Connection tracking ---

    last_connected_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful connection test",
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Last error from connection test or command execution",
    )

    # --- ORM relationship ---

    agent = relationship(
        "Agent",
        back_populates="compute",
        uselist=False,
    )

    # --- Credential helpers ---

    def set_credentials(self, credentials: str) -> None:
        """Encrypt and store SSH private key or password."""
        from src.services.agents.security import encrypt_value

        self.remote_credentials_encrypted = encrypt_value(credentials)

    def get_credentials(self) -> str | None:
        """Decrypt and return credentials; None if unset."""
        if not self.remote_credentials_encrypted:
            return None
        from src.services.agents.security import decrypt_value

        return decrypt_value(self.remote_credentials_encrypted)

    def to_dict(self) -> dict:
        """Serialize to dict, omitting raw credentials."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "tenant_id": str(self.tenant_id),
            "compute_type": self.compute_type,
            "status": self.status,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "remote_user": self.remote_user,
            "remote_auth_type": self.remote_auth_type,
            "remote_base_path": self.remote_base_path,
            "has_credentials": bool(self.remote_credentials_encrypted),
            "timeout_seconds": self.timeout_seconds,
            "max_output_chars": self.max_output_chars,
            "allowed_commands_override": self.allowed_commands_override,
            "last_connected_at": (self.last_connected_at.isoformat() if self.last_connected_at else None),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<AgentCompute(id={self.id}, agent={self.agent_id}, type={self.compute_type}, status={self.status})>"
