"""Google Drive tool registrations."""

from typing import Any

from src.services.agents.internal_tools.google_drive_tools import (
    internal_google_docs_append_content,
    internal_google_docs_create_document,
    internal_google_docs_get_content,
    internal_google_drive_create_folder,
    internal_google_drive_delete_file,
    internal_google_drive_download_file,
    internal_google_drive_get_file,
    internal_google_drive_get_permissions,
    internal_google_drive_list_files,
    internal_google_drive_move_file,
    internal_google_drive_remove_permission,
    internal_google_drive_search_files,
    internal_google_drive_share_file,
    internal_google_drive_update_file,
    internal_google_drive_upload_file,
    internal_google_sheets_create_spreadsheet,
    internal_google_sheets_read_range,
    internal_google_sheets_write_range,
)


def register_google_drive_tools(adk_tools_instance):
    """Register all Google Drive tools."""

    # Wrapper functions
    async def google_drive_list_files_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_list_files(
            page_size=kwargs.get("page_size", 100),
            page_token=kwargs.get("page_token"),
            query=kwargs.get("query"),
            order_by=kwargs.get("order_by", "modifiedTime desc"),
            spaces=kwargs.get("spaces", "drive"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_get_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_get_file(
            file_id=kwargs.get("file_id"), config=config, runtime_context=runtime_context
        )

    async def google_drive_download_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_download_file(
            file_id=kwargs.get("file_id"), config=config, runtime_context=runtime_context
        )

    async def google_drive_upload_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_upload_file(
            name=kwargs.get("name"),
            content=kwargs.get("content"),
            mime_type=kwargs.get("mime_type"),
            parent_folder_id=kwargs.get("parent_folder_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_update_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_update_file(
            file_id=kwargs.get("file_id"),
            name=kwargs.get("name"),
            content=kwargs.get("content"),
            mime_type=kwargs.get("mime_type"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_delete_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_delete_file(
            file_id=kwargs.get("file_id"), config=config, runtime_context=runtime_context
        )

    async def google_drive_search_files_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_search_files(
            query=kwargs.get("query"),
            page_size=kwargs.get("page_size", 100),
            order_by=kwargs.get("order_by", "modifiedTime desc"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_create_folder_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_create_folder(
            name=kwargs.get("name"),
            parent_folder_id=kwargs.get("parent_folder_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_move_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_move_file(
            file_id=kwargs.get("file_id"),
            new_parent_id=kwargs.get("new_parent_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_share_file_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_share_file(
            file_id=kwargs.get("file_id"),
            email=kwargs.get("email"),
            role=kwargs.get("role", "reader"),
            send_notification=kwargs.get("send_notification", True),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_drive_get_permissions_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_get_permissions(
            file_id=kwargs.get("file_id"), config=config, runtime_context=runtime_context
        )

    async def google_drive_remove_permission_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_drive_remove_permission(
            file_id=kwargs.get("file_id"),
            permission_id=kwargs.get("permission_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_docs_create_document_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_docs_create_document(
            title=kwargs.get("title"), content=kwargs.get("content"), config=config, runtime_context=runtime_context
        )

    async def google_docs_get_content_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_docs_get_content(
            document_id=kwargs.get("document_id"), config=config, runtime_context=runtime_context
        )

    async def google_docs_append_content_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_docs_append_content(
            document_id=kwargs.get("document_id"),
            content=kwargs.get("content"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_sheets_create_spreadsheet_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_sheets_create_spreadsheet(
            title=kwargs.get("title"), config=config, runtime_context=runtime_context
        )

    async def google_sheets_read_range_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_sheets_read_range(
            spreadsheet_id=kwargs.get("spreadsheet_id"),
            range_name=kwargs.get("range_name"),
            config=config,
            runtime_context=runtime_context,
        )

    async def google_sheets_write_range_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_google_sheets_write_range(
            spreadsheet_id=kwargs.get("spreadsheet_id"),
            range_name=kwargs.get("range_name"),
            values=kwargs.get("values"),
            config=config,
            runtime_context=runtime_context,
        )

    # Register all tools
    adk_tools_instance.register_tool(
        name="internal_google_drive_list_files",
        description="List files and folders in Google Drive with pagination, filtering, and sorting.",
        parameters={
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "integer",
                    "description": "Number of files to return per page (max 1000, default: 100)",
                    "default": 100,
                },
                "page_token": {"type": "string", "description": "Token for next page of results"},
                "query": {"type": "string", "description": "Search query using Google Drive query syntax"},
                "order_by": {
                    "type": "string",
                    "description": "Sort order (default: 'modifiedTime desc')",
                    "default": "modifiedTime desc",
                },
                "spaces": {
                    "type": "string",
                    "description": "Space to search in: drive, appDataFolder, photos",
                    "default": "drive",
                },
            },
            "required": [],
        },
        function=google_drive_list_files_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_get_file",
        description="Get metadata for a specific file or folder in Google Drive.",
        parameters={
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "Google Drive file ID"}},
            "required": ["file_id"],
        },
        function=google_drive_get_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_download_file",
        description="Download file content from Google Drive. Returns base64-encoded content for binary files.",
        parameters={
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "Google Drive file ID"}},
            "required": ["file_id"],
        },
        function=google_drive_download_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_upload_file",
        description="Upload a new file to Google Drive. Content should be base64-encoded for binary files.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "File name"},
                "content": {"type": "string", "description": "File content (base64-encoded for binary files)"},
                "mime_type": {"type": "string", "description": "MIME type (e.g., 'text/plain', 'image/png')"},
                "parent_folder_id": {"type": "string", "description": "Parent folder ID (optional)"},
            },
            "required": ["name", "content", "mime_type"],
        },
        function=google_drive_upload_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_update_file",
        description="Update an existing file's metadata or content in Google Drive.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID"},
                "name": {"type": "string", "description": "New file name (optional)"},
                "content": {"type": "string", "description": "New file content (optional)"},
                "mime_type": {"type": "string", "description": "New MIME type (optional)"},
            },
            "required": ["file_id"],
        },
        function=google_drive_update_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_delete_file",
        description="Delete a file or folder from Google Drive.",
        parameters={
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "Google Drive file ID"}},
            "required": ["file_id"],
        },
        function=google_drive_delete_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_search_files",
        description="Search for files in Google Drive using query syntax.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query using Google Drive query syntax"},
                "page_size": {"type": "integer", "description": "Number of files to return", "default": 100},
                "order_by": {"type": "string", "description": "Sort order", "default": "modifiedTime desc"},
            },
            "required": ["query"],
        },
        function=google_drive_search_files_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_create_folder",
        description="Create a new folder in Google Drive.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Folder name"},
                "parent_folder_id": {"type": "string", "description": "Parent folder ID (optional)"},
            },
            "required": ["name"],
        },
        function=google_drive_create_folder_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_move_file",
        description="Move a file to a different folder in Google Drive.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "File ID to move"},
                "new_parent_id": {"type": "string", "description": "New parent folder ID"},
            },
            "required": ["file_id", "new_parent_id"],
        },
        function=google_drive_move_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_share_file",
        description="Share a file with a user via email.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "File ID to share"},
                "email": {"type": "string", "description": "Email address of the user"},
                "role": {
                    "type": "string",
                    "description": "Permission role: reader, writer, commenter",
                    "default": "reader",
                },
                "send_notification": {"type": "boolean", "description": "Send email notification", "default": True},
            },
            "required": ["file_id", "email"],
        },
        function=google_drive_share_file_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_get_permissions",
        description="Get permissions list for a file.",
        parameters={
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "File ID"}},
            "required": ["file_id"],
        },
        function=google_drive_get_permissions_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_drive_remove_permission",
        description="Remove a permission from a file.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "File ID"},
                "permission_id": {"type": "string", "description": "Permission ID to remove"},
            },
            "required": ["file_id", "permission_id"],
        },
        function=google_drive_remove_permission_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_docs_create_document",
        description="Create a new Google Docs document.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Initial document content (optional)"},
            },
            "required": ["title"],
        },
        function=google_docs_create_document_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_docs_get_content",
        description="Get content from a Google Docs document.",
        parameters={
            "type": "object",
            "properties": {"document_id": {"type": "string", "description": "Document ID"}},
            "required": ["document_id"],
        },
        function=google_docs_get_content_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_docs_append_content",
        description="Append content to a Google Docs document.",
        parameters={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"},
                "content": {"type": "string", "description": "Content to append"},
            },
            "required": ["document_id", "content"],
        },
        function=google_docs_append_content_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_sheets_create_spreadsheet",
        description="Create a new Google Sheets spreadsheet.",
        parameters={
            "type": "object",
            "properties": {"title": {"type": "string", "description": "Spreadsheet title"}},
            "required": ["title"],
        },
        function=google_sheets_create_spreadsheet_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_sheets_read_range",
        description="Read data from a range in a Google Sheets spreadsheet.",
        parameters={
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Spreadsheet ID"},
                "range_name": {"type": "string", "description": "Range in A1 notation (e.g., 'Sheet1!A1:D10')"},
            },
            "required": ["spreadsheet_id", "range_name"],
        },
        function=google_sheets_read_range_wrapper,
        requires_auth="google_drive",
    )

    adk_tools_instance.register_tool(
        name="internal_google_sheets_write_range",
        description="Write data to a range in a Google Sheets spreadsheet.",
        parameters={
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Spreadsheet ID"},
                "range_name": {"type": "string", "description": "Range in A1 notation (e.g., 'Sheet1!A1')"},
                "values": {
                    "type": "array",
                    "description": "2D array of values to write. Each row is an array of cell values.",
                    "items": {
                        "type": "array",
                        "items": {"type": "string", "description": "Cell value (can be string, number, etc.)"},
                    },
                },
            },
            "required": ["spreadsheet_id", "range_name", "values"],
        },
        function=google_sheets_write_range_wrapper,
        requires_auth="google_drive",
    )
