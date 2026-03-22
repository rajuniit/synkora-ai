"""
Upload file model for managing file uploads.
"""

from enum import StrEnum
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class FileType(StrEnum):
    """File type enumeration."""

    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    OTHER = "OTHER"


class FileSource(StrEnum):
    """File source enumeration."""

    UPLOAD = "UPLOAD"
    URL = "URL"
    GENERATED = "GENERATED"


class UploadFile(Base, UUIDMixin, TimestampMixin):
    """
    Upload file model.

    Stores metadata about uploaded files.
    """

    __tablename__ = "upload_files"

    # Foreign keys
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    size: Mapped[int] = mapped_column(nullable=False)  # Size in bytes
    extension: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # File type and source
    file_type: Mapped[FileType] = mapped_column(
        String(50),
        nullable=False,
        default=FileType.OTHER,
    )
    source: Mapped[FileSource] = mapped_column(
        String(50),
        nullable=False,
        default=FileSource.UPLOAD,
    )

    # Storage information
    storage_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="local",
    )  # local, s3, azure, etc.

    # Optional metadata
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        type_=Text,
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="files")
    creator: Mapped[Optional["Account"]] = relationship()

    def __repr__(self) -> str:
        """String representation."""
        return f"<UploadFile {self.name} ({self.file_type})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "created_by": str(self.created_by) if self.created_by else None,
            "name": self.name,
            "key": self.key,
            "size": self.size,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "file_type": self.file_type.value,
            "source": self.source.value,
            "storage_type": self.storage_type,
            "hash": self.hash,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def url(self) -> str:
        """Get file URL (to be implemented based on storage type)."""
        # This will be implemented in the storage service
        return f"/files/{self.id}"

    @property
    def size_mb(self) -> float:
        """Get file size in MB."""
        return self.size / (1024 * 1024)

    def is_image(self) -> bool:
        """Check if file is an image."""
        return self.file_type == FileType.IMAGE

    def is_document(self) -> bool:
        """Check if file is a document."""
        return self.file_type == FileType.DOCUMENT
