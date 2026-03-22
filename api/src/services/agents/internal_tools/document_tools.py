"""
Generic Document Generation Tools.

Provides universal document generation tools that can be used by any agent
to create PDF, PowerPoint, Google Docs, and Google Sheets documents.
"""

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


async def internal_generate_pdf(
    content: str,
    title: str = "Document",
    filename: str | None = None,
    author: str = "Synkora Agent",
    include_metadata: bool = True,
    config: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a PDF document from markdown or plain text content.

    Use this tool to create professional PDF documents from any text content.
    Supports markdown formatting including headers, bold, italic, lists, and more.

    Args:
        content: Document content (supports markdown formatting)
        title: Document title
        filename: Optional custom filename (without extension)
        author: Document author name
        include_metadata: Include generation timestamp and author
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with success status, file_path, file_name, and file_size
    """
    try:
        from src.core.database import get_async_session_factory
        from src.services.document_generation_service import DocumentGenerationService

        # Get tenant_id from runtime context
        # Handle both dict and RuntimeContext object
        tenant_id = None
        if runtime_context:
            if isinstance(runtime_context, dict):
                tenant_id = runtime_context.get("tenant_id")
            else:
                tenant_id = getattr(runtime_context, "tenant_id", None)

        if not tenant_id:
            return {"success": False, "error": "Tenant ID not found in runtime context"}

        # Get database session
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as db:
            # Create document generation service
            doc_service = DocumentGenerationService(db, UUID(str(tenant_id)))

            # Generate PDF
            result = await doc_service.generate_pdf(
                content=content, filename=filename, title=title, author=author, include_metadata=include_metadata
            )

            return result

    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"PDF generation failed: {str(e)}"}


async def internal_generate_powerpoint(
    slides_content: list[dict[str, Any]],
    title: str = "Presentation",
    filename: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a PowerPoint presentation.

    Create professional PowerPoint presentations with multiple slides.
    Each slide can have a title and either content text or bullet points.

    Args:
        slides_content: List of slide dictionaries, each containing:
            - title: Slide title (string)
            - content: Slide content text (string), OR
            - bullet_points: List of bullet point strings
        title: Presentation title (for title slide)
        filename: Optional custom filename (without extension)
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with success status, file_path, file_name, file_size, and slide count

    Example slides_content:
        [
            {"title": "Introduction", "bullet_points": ["Point 1", "Point 2", "Point 3"]},
            {"title": "Details", "content": "Detailed information about the topic..."}
        ]
    """
    try:
        from src.core.database import get_async_session_factory
        from src.services.document_generation_service import DocumentGenerationService

        # Get tenant_id from runtime context
        # Handle both dict and RuntimeContext object
        tenant_id = None
        if runtime_context:
            if isinstance(runtime_context, dict):
                tenant_id = runtime_context.get("tenant_id")
            else:
                tenant_id = getattr(runtime_context, "tenant_id", None)

        if not tenant_id:
            return {"success": False, "error": "Tenant ID not found in runtime context"}

        # Get database session
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as db:
            # Create document generation service
            doc_service = DocumentGenerationService(db, UUID(str(tenant_id)))

            # Generate PowerPoint
            result = await doc_service.generate_powerpoint(
                slides_content=slides_content, filename=filename, title=title
            )

            return result

    except Exception as e:
        logger.error(f"Failed to generate PowerPoint: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"PowerPoint generation failed: {str(e)}"}


async def internal_generate_google_doc(
    content: str,
    title: str = "Document",
    share_with_emails: list[str] | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a Google Doc and optionally share it.

    Create a document in Google Docs that can be collaboratively edited.
    Requires Google API OAuth configuration.

    Args:
        content: Document content
        title: Document title
        share_with_emails: Optional list of email addresses to share with
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with success status, document URL, and document ID

    Note:
        This feature requires Google API OAuth setup. If not configured,
        you'll receive instructions on how to set it up.
    """
    try:
        from src.core.database import get_async_session_factory
        from src.services.document_generation_service import DocumentGenerationService

        # Get tenant_id from runtime context
        # Handle both dict and RuntimeContext object
        tenant_id = None
        if runtime_context:
            if isinstance(runtime_context, dict):
                tenant_id = runtime_context.get("tenant_id")
            else:
                tenant_id = getattr(runtime_context, "tenant_id", None)

        if not tenant_id:
            return {"success": False, "error": "Tenant ID not found in runtime context"}

        # Get database session
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as db:
            # Create document generation service
            doc_service = DocumentGenerationService(db, UUID(str(tenant_id)))

            # Generate Google Doc
            result = await doc_service.generate_google_doc(
                content=content, title=title, share_with_emails=share_with_emails
            )

            return result

    except Exception as e:
        logger.error(f"Failed to generate Google Doc: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Google Doc generation failed: {str(e)}"}


async def internal_generate_google_sheet(
    data: list[list[Any]],
    title: str = "Spreadsheet",
    sheet_name: str = "Sheet1",
    share_with_emails: list[str] | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a Google Sheet and optionally share it.

    Create a spreadsheet in Google Sheets with tabular data.
    Requires Google API OAuth configuration.

    Args:
        data: 2D array of data (list of rows, each row is a list of cell values)
        title: Spreadsheet title
        sheet_name: Name of the sheet tab
        share_with_emails: Optional list of email addresses to share with
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with success status, spreadsheet URL, and spreadsheet ID

    Example data:
        [
            ["Name", "Age", "City"],
            ["John", 30, "New York"],
            ["Jane", 25, "San Francisco"]
        ]

    Note:
        This feature requires Google API OAuth setup. If not configured,
        you'll receive instructions on how to set it up.
    """
    try:
        from src.core.database import get_async_session_factory
        from src.services.document_generation_service import DocumentGenerationService

        # Get tenant_id from runtime context
        # Handle both dict and RuntimeContext object
        tenant_id = None
        if runtime_context:
            if isinstance(runtime_context, dict):
                tenant_id = runtime_context.get("tenant_id")
            else:
                tenant_id = getattr(runtime_context, "tenant_id", None)

        if not tenant_id:
            return {"success": False, "error": "Tenant ID not found in runtime context"}

        # Get database session
        AsyncSessionLocal = get_async_session_factory()
        async with AsyncSessionLocal() as db:
            # Create document generation service
            doc_service = DocumentGenerationService(db, UUID(str(tenant_id)))

            # Generate Google Sheet
            result = await doc_service.generate_google_sheet(
                data=data, title=title, sheet_name=sheet_name, share_with_emails=share_with_emails
            )

            return result

    except Exception as e:
        logger.error(f"Failed to generate Google Sheet: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Google Sheet generation failed: {str(e)}"}
