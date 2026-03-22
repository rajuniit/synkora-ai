"""Database connection model for universal data analysis tools."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class DatabaseConnectionType(enum.StrEnum):
    """Supported database types (extensible)."""

    POSTGRESQL = "POSTGRESQL"
    ELASTICSEARCH = "ELASTICSEARCH"
    MYSQL = "MYSQL"
    MONGODB = "MONGODB"
    SQLITE = "SQLITE"


# Junction table for many-to-many relationship between database connections and agents
database_connection_agents = Table(
    "database_connection_agents",
    BaseModel.metadata,
    Column(
        "database_connection_id",
        UUID(as_uuid=True),
        ForeignKey("database_connections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("agent_id", UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)


class DatabaseConnection(BaseModel, TimestampMixin):
    """Universal database connections that ANY agent can use."""

    __tablename__ = "database_connections"

    # Note: id is inherited from BaseModel as UUID
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    database_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Connection details (stored in database, not env)
    # These are optional for SQLite which only needs database_path
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    database_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SQLite-specific field
    database_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Additional connection parameters (SSL, timeouts, etc.)
    connection_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active", index=True)

    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="database_connections")

    def __repr__(self) -> str:
        return f"<DatabaseConnection(id={self.id}, name='{self.name}', type='{self.database_type}')>"

    def set_password(self, password: str) -> None:
        """Encrypt and set the password."""
        from src.services.agents.security import encrypt_value

        self.password_encrypted = encrypt_value(password)

    def get_password(self) -> str:
        """Decrypt and return the password."""
        from src.services.agents.security import decrypt_value

        return decrypt_value(self.password_encrypted)

    def to_dict(self, include_agents: bool = False) -> dict:
        """Convert to dictionary (excluding sensitive data)."""
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "type": self.database_type,
            "host": self.host,
            "port": self.port,
            "database": self.database_name,
            "username": self.username,
            "connection_params": self.connection_params or {},
            "status": self.status,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "test_result": self.test_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        return result
