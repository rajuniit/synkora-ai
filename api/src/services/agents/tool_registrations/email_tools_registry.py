"""
Email Tools Registry

Registers all email-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_email_tools(registry):
    """
    Register all email tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.email_tools import (
        internal_send_bulk_emails,
        internal_send_email,
        internal_test_email_connection,
    )

    def _resolve_redacted_email(value: str, runtime_context, field_name: str = "recipient_email") -> str:
        """
        Resolve [EMAIL_REDACTED] placeholder from task_config in shared_state.

        Args:
            value: The potentially redacted email value
            runtime_context: Runtime context with shared_state
            field_name: The field name to look up in task_config (default: recipient_email)
        """
        if not value or "[EMAIL_REDACTED]" not in str(value):
            return value

        if not runtime_context or not runtime_context.shared_state:
            logger.warning("📧 Cannot resolve [EMAIL_REDACTED] - no shared_state")
            return value

        task_config = runtime_context.shared_state.get("task_config", {})
        resolved = task_config.get(field_name)

        if resolved:
            logger.info(f"📧 Resolved [EMAIL_REDACTED] from task_config.{field_name} -> {resolved}")
            return resolved

        logger.warning(f"📧 Could not resolve [EMAIL_REDACTED] - {field_name} not in task_config")
        return value

    # Email tools - create wrappers that inject runtime_context
    async def internal_send_email_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        to_email = kwargs.get("to_email")

        logger.info(f"📧 [send_email] Called with to_email={to_email!r}, subject={kwargs.get('subject')!r}")

        # Resolve [EMAIL_REDACTED] if present
        to_email = _resolve_redacted_email(to_email, runtime_context)

        return await internal_send_email(
            to_email=to_email,
            subject=kwargs.get("subject"),
            body=kwargs.get("body"),
            html=kwargs.get("html", False),
            from_email=kwargs.get("from_email"),
            from_name=kwargs.get("from_name"),
            cc=kwargs.get("cc"),
            bcc=kwargs.get("bcc"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_send_bulk_emails_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_send_bulk_emails(
            recipients=kwargs.get("recipients"),
            subject=kwargs.get("subject"),
            body=kwargs.get("body"),
            html=kwargs.get("html", False),
            from_email=kwargs.get("from_email"),
            from_name=kwargs.get("from_name"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_test_email_connection_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_test_email_connection(runtime_context=runtime_context, config=config)

    # Register all email tools
    registry.register_tool(
        name="internal_send_email",
        description="Send an email to a recipient using the configured email integration (SMTP, SendGrid, Mailgun). Use this when you need to send notifications, updates, or any communication via email. Supports both plain text and HTML content.",
        parameters={
            "type": "object",
            "properties": {
                "to_email": {"type": "string", "description": "Recipient email address (e.g., 'user@example.com')"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {
                    "type": "string",
                    "description": "Email body content (plain text or HTML based on html parameter)",
                },
                "html": {
                    "type": "boolean",
                    "description": "Whether the body contains HTML content (default: false for plain text)",
                    "default": False,
                },
                "from_email": {
                    "type": "string",
                    "description": "Optional sender email address (uses integration config default if not provided)",
                },
                "from_name": {"type": "string", "description": "Optional sender name to display"},
                "cc": {"type": "string", "description": "Optional carbon copy recipients (comma-separated)"},
                "bcc": {"type": "string", "description": "Optional blind carbon copy recipients (comma-separated)"},
            },
            "required": ["to_email", "subject", "body"],
        },
        function=internal_send_email_wrapper,
    )

    registry.register_tool(
        name="internal_send_bulk_emails",
        description="Send the same email to multiple recipients at once. Useful for notifications, announcements, or newsletters. Maximum 100 recipients per call. Each email is sent individually to maintain privacy.",
        parameters={
            "type": "object",
            "properties": {
                "recipients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses (max 100)",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
                "html": {"type": "boolean", "description": "Whether the body contains HTML content", "default": False},
                "from_email": {"type": "string", "description": "Optional sender email address"},
                "from_name": {"type": "string", "description": "Optional sender name"},
            },
            "required": ["recipients", "subject", "body"],
        },
        function=internal_send_bulk_emails_wrapper,
    )

    registry.register_tool(
        name="internal_test_email_connection",
        description="Test the email configuration to verify that the email integration is properly configured and can connect to the email provider. Use this to troubleshoot email issues before attempting to send actual emails.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=internal_test_email_connection_wrapper,
    )

    logger.info("Registered 3 email tools")
