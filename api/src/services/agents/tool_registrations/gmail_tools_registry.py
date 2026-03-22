"""Gmail tool registrations."""

from typing import Any

from src.services.agents.internal_tools.gmail_tools import (
    internal_gmail_bulk_delete,
    internal_gmail_create_draft,
    internal_gmail_delete_draft,
    internal_gmail_delete_email,
    internal_gmail_empty_spam,
    internal_gmail_empty_trash,
    internal_gmail_forward,
    internal_gmail_get_email,
    internal_gmail_get_labels,
    internal_gmail_list_drafts,
    internal_gmail_list_emails,
    internal_gmail_reply,
    internal_gmail_search_emails,
    internal_gmail_send_draft,
    internal_gmail_send_email,
)


def register_gmail_tools(adk_tools_instance):
    """Register all Gmail tools."""

    # Wrapper functions
    async def gmail_list_emails_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_list_emails(
            query=kwargs.get("query"),
            label_ids=kwargs.get("label_ids"),
            max_results=kwargs.get("max_results", 100),
            page_token=kwargs.get("page_token"),
            include_spam_trash=kwargs.get("include_spam_trash", False),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_search_emails_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_search_emails(
            query=kwargs.get("query"),
            max_results=kwargs.get("max_results", 100),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_get_email_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_get_email(
            message_id=kwargs.get("message_id"),
            format=kwargs.get("format", "full"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_delete_email_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_delete_email(
            message_id=kwargs.get("message_id"),
            permanent=kwargs.get("permanent", False),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_bulk_delete_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_bulk_delete(
            query=kwargs.get("query"),
            message_ids=kwargs.get("message_ids"),
            max_delete=kwargs.get("max_delete", 1000),
            permanent=kwargs.get("permanent", False),
            dry_run=kwargs.get("dry_run", False),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_get_labels_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_get_labels(
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_empty_trash_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_empty_trash(
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_empty_spam_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_empty_spam(
            config=config,
            runtime_context=runtime_context,
        )

    # Register all tools
    adk_tools_instance.register_tool(
        name="internal_gmail_list_emails",
        description="List emails from Gmail with optional filtering by query, labels, and pagination. Use Gmail search syntax for powerful filtering.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:example@gmail.com', 'is:unread', 'older_than:7d', 'category:promotions')",
                },
                "label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label IDs to filter (e.g., ['INBOX', 'UNREAD'])",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of emails to return (default: 100, max: 500)",
                    "default": 100,
                },
                "page_token": {
                    "type": "string",
                    "description": "Token for pagination to get next page of results",
                },
                "include_spam_trash": {
                    "type": "boolean",
                    "description": "Whether to include spam and trash (default: false)",
                    "default": False,
                },
            },
            "required": [],
        },
        function=gmail_list_emails_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_search_emails",
        description="Search emails using Gmail query syntax. Returns matching emails with metadata.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (required). Examples: 'from:newsletter@* older_than:30d', 'has:attachment larger:10M', 'category:social'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 100)",
                    "default": 100,
                },
            },
            "required": ["query"],
        },
        function=gmail_search_emails_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_get_email",
        description="Get a single email by ID with full content including body text.",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID",
                },
                "format": {
                    "type": "string",
                    "description": "Response format: 'full', 'metadata', 'minimal', or 'raw'",
                    "default": "full",
                    "enum": ["full", "metadata", "minimal", "raw"],
                },
            },
            "required": ["message_id"],
        },
        function=gmail_get_email_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_delete_email",
        description="Delete a single email by ID. Moves to trash by default, or permanently deletes if specified.",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID to delete",
                },
                "permanent": {
                    "type": "boolean",
                    "description": "If true, permanently deletes. If false, moves to trash (default: false)",
                    "default": False,
                },
            },
            "required": ["message_id"],
        },
        function=gmail_delete_email_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_bulk_delete",
        description="Bulk delete emails matching a Gmail search query or by specific message IDs. Supports dry run to preview count before deleting. Perfect for clearing thousands of promotional emails, old newsletters, or spam.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query to find emails to delete (e.g., 'category:promotions older_than:30d', 'from:newsletter@* older_than:7d')",
                },
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific message IDs to delete (alternative to query)",
                },
                "max_delete": {
                    "type": "integer",
                    "description": "Maximum number of emails to delete (default: 1000, max: 5000)",
                    "default": 1000,
                },
                "permanent": {
                    "type": "boolean",
                    "description": "If true, permanently deletes. If false, moves to trash (default: false)",
                    "default": False,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, only counts matching emails without deleting (default: false). Use this first to verify the query.",
                    "default": False,
                },
            },
            "required": [],
        },
        function=gmail_bulk_delete_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_get_labels",
        description="Get all Gmail labels including system labels (INBOX, SENT, TRASH) and user-created labels.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=gmail_get_labels_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_empty_trash",
        description="Empty the Gmail trash folder, permanently deleting all trashed emails. WARNING: This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=gmail_empty_trash_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_empty_spam",
        description="Empty the Gmail spam folder, permanently deleting all spam emails. WARNING: This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=gmail_empty_spam_wrapper,
        requires_auth="gmail",
    )

    # === Email Composition Tools ===

    async def gmail_send_email_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_send_email(
            to=kwargs.get("to"),
            subject=kwargs.get("subject"),
            body=kwargs.get("body"),
            cc=kwargs.get("cc"),
            bcc=kwargs.get("bcc"),
            html=kwargs.get("html", False),
            attachments=kwargs.get("attachments"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_reply_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_reply(
            message_id=kwargs.get("message_id"),
            body=kwargs.get("body"),
            reply_all=kwargs.get("reply_all", False),
            html=kwargs.get("html", False),
            attachments=kwargs.get("attachments"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_forward_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_forward(
            message_id=kwargs.get("message_id"),
            to=kwargs.get("to"),
            additional_message=kwargs.get("additional_message"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_create_draft_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_create_draft(
            to=kwargs.get("to"),
            subject=kwargs.get("subject"),
            body=kwargs.get("body"),
            cc=kwargs.get("cc"),
            bcc=kwargs.get("bcc"),
            html=kwargs.get("html", False),
            reply_to_message_id=kwargs.get("reply_to_message_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_list_drafts_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_list_drafts(
            max_results=kwargs.get("max_results", 100),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_send_draft_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_send_draft(
            draft_id=kwargs.get("draft_id"),
            config=config,
            runtime_context=runtime_context,
        )

    async def gmail_delete_draft_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_gmail_delete_draft(
            draft_id=kwargs.get("draft_id"),
            config=config,
            runtime_context=runtime_context,
        )

    # Register email composition tools
    adk_tools_instance.register_tool(
        name="internal_gmail_send_email",
        description="Send an email through Gmail. Supports HTML content, CC/BCC, and attachments from URLs.",
        parameters={
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Email body content (plain text or HTML if html=true)",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of CC recipient email addresses",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of BCC recipient email addresses",
                },
                "html": {
                    "type": "boolean",
                    "description": "If true, body is treated as HTML content (default: false)",
                    "default": False,
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "url": {"type": "string"},
                            "content_type": {"type": "string"},
                        },
                        "required": ["filename", "url"],
                    },
                    "description": "List of attachments with filename and URL",
                },
            },
            "required": ["to", "subject", "body"],
        },
        function=gmail_send_email_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_reply",
        description="Reply to an existing email. Automatically maintains conversation thread and formats reply headers.",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID of the email to reply to",
                },
                "body": {
                    "type": "string",
                    "description": "Reply body content",
                },
                "reply_all": {
                    "type": "boolean",
                    "description": "If true, replies to all recipients (default: false)",
                    "default": False,
                },
                "html": {
                    "type": "boolean",
                    "description": "If true, body is treated as HTML content (default: false)",
                    "default": False,
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "url": {"type": "string"},
                            "content_type": {"type": "string"},
                        },
                        "required": ["filename", "url"],
                    },
                    "description": "List of attachments with filename and URL",
                },
            },
            "required": ["message_id", "body"],
        },
        function=gmail_reply_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_forward",
        description="Forward an email to new recipients. Includes original message content and optional additional message.",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID of the email to forward",
                },
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses to forward to",
                },
                "additional_message": {
                    "type": "string",
                    "description": "Optional message to include before the forwarded content",
                },
            },
            "required": ["message_id", "to"],
        },
        function=gmail_forward_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_create_draft",
        description="Create a draft email in Gmail. Can be a new email or a reply draft to an existing message.",
        parameters={
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "Email body content",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of CC recipient email addresses",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of BCC recipient email addresses",
                },
                "html": {
                    "type": "boolean",
                    "description": "If true, body is treated as HTML content (default: false)",
                    "default": False,
                },
                "reply_to_message_id": {
                    "type": "string",
                    "description": "Gmail message ID if this draft is a reply to an existing email",
                },
            },
            "required": ["to", "subject", "body"],
        },
        function=gmail_create_draft_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_list_drafts",
        description="List all draft emails in Gmail with their metadata.",
        parameters={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of drafts to return (default: 100)",
                    "default": 100,
                },
            },
            "required": [],
        },
        function=gmail_list_drafts_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_send_draft",
        description="Send an existing draft email. The draft is deleted after sending.",
        parameters={
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "Gmail draft ID to send",
                },
            },
            "required": ["draft_id"],
        },
        function=gmail_send_draft_wrapper,
        requires_auth="gmail",
    )

    adk_tools_instance.register_tool(
        name="internal_gmail_delete_draft",
        description="Delete a draft email from Gmail. This action is irreversible.",
        parameters={
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "Gmail draft ID to delete",
                },
            },
            "required": ["draft_id"],
        },
        function=gmail_delete_draft_wrapper,
        requires_auth="gmail",
    )
