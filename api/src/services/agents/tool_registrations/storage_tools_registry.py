"""
S3 Storage Tools Registry

Registers all S3 storage-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_storage_tools(registry):
    """
    Register all S3 storage tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.storage_tools import (
        internal_s3_delete_file,
        internal_s3_download_file,
        internal_s3_file_exists,
        internal_s3_generate_presigned_url,
        internal_s3_get_file_metadata,
        internal_s3_list_files,
        internal_s3_upload_directory,
        internal_s3_upload_file,
    )

    # S3 Storage Tools - create wrappers that inject runtime_context
    async def internal_s3_upload_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_upload_file(
            file_path=kwargs.get("file_path"),
            s3_key=kwargs.get("s3_key"),
            content_type=kwargs.get("content_type"),
            metadata=kwargs.get("metadata"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_s3_upload_directory_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_upload_directory(
            directory_path=kwargs.get("directory_path"),
            base_prefix=kwargs.get("base_prefix"),
            tenant_id=kwargs.get("tenant_id"),
            metadata=kwargs.get("metadata"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_s3_download_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_download_file(
            s3_key=kwargs.get("s3_key"),
            output_path=kwargs.get("output_path"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_s3_generate_presigned_url_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_generate_presigned_url(
            s3_key=kwargs.get("s3_key"),
            expiration=kwargs.get("expiration", 3600),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_s3_list_files_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_list_files(
            prefix=kwargs.get("prefix", ""),
            max_keys=kwargs.get("max_keys", 1000),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_s3_delete_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_delete_file(
            s3_key=kwargs.get("s3_key"), config=config, runtime_context=runtime_context
        )

    async def internal_s3_file_exists_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_file_exists(
            s3_key=kwargs.get("s3_key"), config=config, runtime_context=runtime_context
        )

    async def internal_s3_get_file_metadata_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_s3_get_file_metadata(
            s3_key=kwargs.get("s3_key"), config=config, runtime_context=runtime_context
        )

    registry.register_tool(
        name="internal_s3_upload_file",
        description="Upload a single file to S3 storage. Returns S3 URL and presigned URL for access.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the local file to upload"},
                "s3_key": {"type": "string", "description": "S3 object key (optional, defaults to filename)"},
                "content_type": {"type": "string", "description": "MIME type of the file (optional)"},
                "metadata": {"type": "object", "description": "Additional metadata to attach (optional)"},
            },
            "required": ["file_path"],
        },
        function=internal_s3_upload_file_wrapper,
    )

    registry.register_tool(
        name="internal_s3_upload_directory",
        description="Upload an entire directory to S3 storage. Perfect for uploading tutorial directories with multiple files. Returns presigned URLs for all uploaded files including index.md. URLs are valid for 7 days. IMPORTANT: After calling this tool, you MUST share the 'index_url' with the user so they can access the uploaded content.",
        parameters={
            "type": "object",
            "properties": {
                "directory_path": {"type": "string", "description": "Path to the local directory to upload"},
                "base_prefix": {
                    "type": "string",
                    "description": "Base S3 prefix/path for uploaded files (e.g., 'tutorials/project-name')",
                },
                "tenant_id": {"type": "string", "description": "Optional tenant ID for organizing files"},
                "metadata": {"type": "object", "description": "Common metadata to attach to all files (optional)"},
            },
            "required": ["directory_path", "base_prefix"],
        },
        function=internal_s3_upload_directory_wrapper,
    )

    registry.register_tool(
        name="internal_s3_download_file",
        description="Download a file from S3 storage to local filesystem.",
        parameters={
            "type": "object",
            "properties": {
                "s3_key": {"type": "string", "description": "S3 object key or S3 URI (s3://bucket/key)"},
                "output_path": {"type": "string", "description": "Optional local path to save the file"},
            },
            "required": ["s3_key"],
        },
        function=internal_s3_download_file_wrapper,
    )

    registry.register_tool(
        name="internal_s3_generate_presigned_url",
        description="Generate a presigned URL for temporary access to an S3 object. Useful for sharing files securely.",
        parameters={
            "type": "object",
            "properties": {
                "s3_key": {"type": "string", "description": "S3 object key or S3 URI"},
                "expiration": {
                    "type": "integer",
                    "description": "URL expiration time in seconds (default: 3600 = 1 hour)",
                },
            },
            "required": ["s3_key"],
        },
        function=internal_s3_generate_presigned_url_wrapper,
    )

    registry.register_tool(
        name="internal_s3_list_files",
        description="List files in S3 with a given prefix. Useful for browsing uploaded tutorials or finding specific files.",
        parameters={
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": "Key prefix to filter by (e.g., 'tutorials/project-name/')",
                },
                "max_keys": {"type": "integer", "description": "Maximum number of keys to return (default: 1000)"},
            },
            "required": [],
        },
        function=internal_s3_list_files_wrapper,
    )

    registry.register_tool(
        name="internal_s3_delete_file",
        description="Delete a file from S3 storage.",
        parameters={
            "type": "object",
            "properties": {"s3_key": {"type": "string", "description": "S3 object key"}},
            "required": ["s3_key"],
        },
        function=internal_s3_delete_file_wrapper,
    )

    registry.register_tool(
        name="internal_s3_file_exists",
        description="Check if a file exists in S3 storage.",
        parameters={
            "type": "object",
            "properties": {"s3_key": {"type": "string", "description": "S3 object key"}},
            "required": ["s3_key"],
        },
        function=internal_s3_file_exists_wrapper,
    )

    registry.register_tool(
        name="internal_s3_get_file_metadata",
        description="Get metadata for a file in S3 storage including size, content type, and last modified date.",
        parameters={
            "type": "object",
            "properties": {"s3_key": {"type": "string", "description": "S3 object key"}},
            "required": ["s3_key"],
        },
        function=internal_s3_get_file_metadata_wrapper,
    )

    logger.info("Registered 8 S3 storage tools")
