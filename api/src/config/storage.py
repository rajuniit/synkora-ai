"""
Storage configuration for file uploads.
"""

import logging
import os
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class StorageConfig(BaseSettings):
    """Storage configuration."""

    # Storage type: local, s3, azure, etc.
    STORAGE_TYPE: Literal["local", "s3", "azure"] = "local"

    @model_validator(mode="after")
    def validate_production_storage(self) -> "StorageConfig":
        """
        Validate that local storage is not used in production.

        K8s pods are ephemeral - local storage violates statelessness
        and causes data loss on pod restart/scaling.
        """
        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")

        if is_production and self.STORAGE_TYPE == "local":
            logger.error(
                "CRITICAL: Local storage is not allowed in production/staging. "
                "Set STORAGE_TYPE=s3 or STORAGE_TYPE=azure for K8s deployments."
            )
            raise ValueError(
                "Local storage (STORAGE_TYPE=local) is not allowed in production. "
                "Use S3 or Azure storage for K8s deployments to ensure data persistence."
            )

        return self

    # Local storage settings
    STORAGE_LOCAL_PATH: str = "storage"

    # S3 storage settings
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT: str = ""  # For S3-compatible services

    # Azure storage settings
    AZURE_STORAGE_ACCOUNT: str = ""
    AZURE_STORAGE_KEY: str = ""
    AZURE_CONTAINER: str = ""

    # File upload limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB default
    ALLOWED_EXTENSIONS: set[str] = {
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".md",
        ".csv",
        ".xls",
        ".xlsx",
        # Audio
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        # Video
        ".mp4",
        ".avi",
        ".mov",
        ".webm",
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )

    @property
    def local_storage_path(self) -> Path:
        """Get local storage path as Path object."""
        path = Path(self.STORAGE_LOCAL_PATH)
        if not path.is_absolute():
            # Make it relative to project root
            path = Path.cwd() / path
        return path

    def ensure_local_storage(self) -> None:
        """Ensure local storage directory exists."""
        if self.STORAGE_TYPE == "local":
            self.local_storage_path.mkdir(parents=True, exist_ok=True)


# Global storage config instance
storage_config = StorageConfig()


def get_storage_service():
    """
    Get storage service instance based on configuration.

    Returns a simple storage service wrapper that handles file operations
    based on the configured storage type (local, S3, Azure).
    """
    from pathlib import Path

    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError

    class StorageService:
        """Simple storage service for file operations."""

        def __init__(self, config: StorageConfig):
            self.config = config
            if config.STORAGE_TYPE == "local":
                config.ensure_local_storage()
            elif config.STORAGE_TYPE == "s3":
                # Force signature version 4 for MinIO compatibility
                import logging

                logger = logging.getLogger(__name__)

                boto_config = Config(signature_version="s3v4", s3={"addressing_style": "path"})

                self.s3_client = boto3.client(
                    "s3",
                    region_name=config.S3_REGION,
                    aws_access_key_id=config.S3_ACCESS_KEY or None,
                    aws_secret_access_key=config.S3_SECRET_KEY or None,
                    endpoint_url=config.S3_ENDPOINT or None,
                    config=boto_config,
                )

                logger.info(
                    f"[get_storage_service] S3 client initialized with signature_version='s3v4', endpoint={config.S3_ENDPOINT}"
                )

        def save_file(self, file_path: str, content: bytes) -> str:
            """
            Save file to storage.

            Args:
                file_path: Relative file path
                content: File content as bytes

            Returns:
                Full path to saved file (for local) or S3 key (for S3)
            """
            if self.config.STORAGE_TYPE == "local":
                full_path = self.config.local_storage_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_bytes(content)
                return str(full_path)
            elif self.config.STORAGE_TYPE == "s3":
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.config.S3_BUCKET,
                    Key=file_path,
                    Body=content,
                    ContentType=self._get_content_type(file_path),
                )
                return file_path  # Return S3 key
            elif self.config.STORAGE_TYPE == "azure":
                raise NotImplementedError("Azure storage not yet implemented")
            else:
                raise ValueError(f"Unsupported storage type: {self.config.STORAGE_TYPE}")

        def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
            """
            Generate a presigned URL for file download.

            Args:
                file_path: Relative file path or S3 key
                expiration: URL expiration time in seconds (default: 1 hour)

            Returns:
                Presigned URL for file access
            """
            if self.config.STORAGE_TYPE == "s3":
                try:
                    import logging

                    logger = logging.getLogger(__name__)

                    logger.info(
                        f"[get_storage_service] Generating presigned URL for: {file_path}, expiration: {expiration}s"
                    )

                    url = self.s3_client.generate_presigned_url(
                        "get_object", Params={"Bucket": self.config.S3_BUCKET, "Key": file_path}, ExpiresIn=expiration
                    )

                    # Log signature version
                    if "X-Amz-Algorithm" in url:
                        logger.info("[get_storage_service] ✅ Generated signature v4 URL")
                    elif "AWSAccessKeyId" in url:
                        logger.error("[get_storage_service] ❌ Generated signature v2 URL (WRONG!)")
                    logger.debug(f"[get_storage_service] URL: {url[:100]}...")

                    return url
                except ClientError as e:
                    raise Exception(f"Failed to generate presigned URL: {e}")
            elif self.config.STORAGE_TYPE == "local":
                # For local storage, return a path that should be served via API
                # The API should have an endpoint to serve these files
                return f"/api/files/{file_path}"
            else:
                raise NotImplementedError(f"Presigned URLs not implemented for {self.config.STORAGE_TYPE}")

        def _get_content_type(self, file_path: str) -> str:
            """Get content type based on file extension."""
            ext = Path(file_path).suffix.lower()
            content_types = {
                ".pdf": "application/pdf",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
            }
            return content_types.get(ext, "application/octet-stream")

        def get_file_path(self, file_path: str) -> Path:
            """
            Get full path to a file in storage.

            Args:
                file_path: Relative file path

            Returns:
                Full path to file
            """
            if self.config.STORAGE_TYPE == "local":
                return self.config.local_storage_path / file_path
            else:
                raise NotImplementedError(f"{self.config.STORAGE_TYPE} storage not yet implemented")

        def delete_file(self, file_path: str) -> bool:
            """
            Delete file from storage.

            Args:
                file_path: Relative file path

            Returns:
                True if deleted successfully
            """
            if self.config.STORAGE_TYPE == "local":
                full_path = self.config.local_storage_path / file_path
                if full_path.exists():
                    full_path.unlink()
                    return True
                return False
            else:
                raise NotImplementedError(f"{self.config.STORAGE_TYPE} storage not yet implemented")

    return StorageService(storage_config)
