"""
Document Generation Tools Registry

Registers all document generation tools with the ADK tool registry.
These tools can be used by any agent to generate PDF, PowerPoint,
Google Docs, and Google Sheets documents.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_document_tools(registry):
    """
    Register all document generation tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.document_tools import (
        internal_generate_google_doc,
        internal_generate_google_sheet,
        internal_generate_pdf,
        internal_generate_powerpoint,
    )

    # Document generation tools - create wrappers that inject runtime_context
    async def internal_generate_pdf_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None

        # Validate required parameter
        if "content" not in kwargs or kwargs.get("content") is None:
            return {
                "success": False,
                "error": "Missing required parameter: 'content'",
                "message": "The 'content' parameter is required to generate a PDF. Please provide the document content you want to convert to PDF format.",
            }

        return await internal_generate_pdf(
            content=kwargs.get("content"),
            title=kwargs.get("title", "Document"),
            filename=kwargs.get("filename"),
            author=kwargs.get("author", "Synkora Agent"),
            include_metadata=kwargs.get("include_metadata", True),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_generate_powerpoint_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_generate_powerpoint(
            slides_content=kwargs.get("slides_content"),
            title=kwargs.get("title", "Presentation"),
            filename=kwargs.get("filename"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_generate_google_doc_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_generate_google_doc(
            content=kwargs.get("content"),
            title=kwargs.get("title", "Document"),
            share_with_emails=kwargs.get("share_with_emails"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_generate_google_sheet_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_generate_google_sheet(
            data=kwargs.get("data"),
            title=kwargs.get("title", "Spreadsheet"),
            sheet_name=kwargs.get("sheet_name", "Sheet1"),
            share_with_emails=kwargs.get("share_with_emails"),
            runtime_context=runtime_context,
            config=config,
        )

    # Register PDF generation tool
    registry.register_tool(
        name="internal_generate_pdf",
        description="Generate a professional PDF document from markdown or plain text content. Supports markdown formatting including headers, bold, italic, lists, code blocks, and more. Perfect for creating reports, reviews, documentation, or any formatted document. The PDF is automatically uploaded to storage and a download link is returned.",
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The document content. Supports markdown formatting: # for headers, ** for bold, * for italic, - for lists, ``` for code blocks, etc. Use plain text if markdown is not needed.",
                },
                "title": {
                    "type": "string",
                    "description": "The document title that appears at the top of the PDF",
                    "default": "Document",
                },
                "filename": {
                    "type": "string",
                    "description": "Optional custom filename (without .pdf extension). If not provided, a filename will be auto-generated from the title and timestamp.",
                },
                "author": {
                    "type": "string",
                    "description": "The author name to include in the PDF metadata",
                    "default": "Synkora Agent",
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Whether to include generation timestamp and author information in the PDF",
                    "default": True,
                },
            },
            "required": ["content"],
        },
        function=internal_generate_pdf_wrapper,
    )

    # Register PowerPoint generation tool
    registry.register_tool(
        name="internal_generate_powerpoint",
        description="Generate a professional PowerPoint presentation with multiple slides. Each slide can have a title and either content text or bullet points. Perfect for creating presentations, reports, summaries, or visual content. The presentation is automatically uploaded to storage.",
        parameters={
            "type": "object",
            "properties": {
                "slides_content": {
                    "type": "array",
                    "description": "List of slide objects. Each slide must have a 'title' field and either 'content' (string) or 'bullet_points' (array of strings)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Slide title"},
                            "content": {
                                "type": "string",
                                "description": "Slide content text (use this OR bullet_points)",
                            },
                            "bullet_points": {
                                "type": "array",
                                "description": "List of bullet points for the slide (use this OR content)",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["title"],
                    },
                },
                "title": {
                    "type": "string",
                    "description": "Presentation title (displayed on the title slide)",
                    "default": "Presentation",
                },
                "filename": {"type": "string", "description": "Optional custom filename (without .pptx extension)"},
            },
            "required": ["slides_content"],
        },
        function=internal_generate_powerpoint_wrapper,
    )

    # Register Google Docs generation tool
    registry.register_tool(
        name="internal_generate_google_doc",
        description="Generate a Google Doc that can be collaboratively edited and shared. Creates a document in Google Docs and optionally shares it with specified email addresses. Note: This requires Google API OAuth configuration. If not set up, you'll receive setup instructions.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The document content"},
                "title": {"type": "string", "description": "The document title", "default": "Document"},
                "share_with_emails": {
                    "type": "array",
                    "description": "Optional list of email addresses to share the document with (grants edit access)",
                    "items": {"type": "string"},
                },
            },
            "required": ["content"],
        },
        function=internal_generate_google_doc_wrapper,
    )

    # Register Google Sheets generation tool
    registry.register_tool(
        name="internal_generate_google_sheet",
        description="Generate a Google Sheet with tabular data that can be collaboratively edited. Creates a spreadsheet in Google Sheets and optionally shares it with specified email addresses. Perfect for structured data, tables, reports, or data analysis. Note: This requires Google API OAuth configuration.",
        parameters={
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "2D array of data where each inner array represents a row. Example: [['Name', 'Age'], ['John', 30], ['Jane', 25]]",
                    "items": {"type": "array", "items": {"type": ["string", "number", "boolean", "null"]}},
                },
                "title": {"type": "string", "description": "The spreadsheet title", "default": "Spreadsheet"},
                "sheet_name": {"type": "string", "description": "The name of the sheet tab", "default": "Sheet1"},
                "share_with_emails": {
                    "type": "array",
                    "description": "Optional list of email addresses to share the spreadsheet with (grants edit access)",
                    "items": {"type": "string"},
                },
            },
            "required": ["data"],
        },
        function=internal_generate_google_sheet_wrapper,
    )

    logger.info("Registered 4 document generation tools (PDF, PowerPoint, Google Docs, Google Sheets)")
