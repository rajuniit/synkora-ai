"""Base email provider interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseEmailProvider(ABC):
    """Abstract base class for email providers."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the email provider with configuration.

        Args:
            config: Provider configuration dictionary
        """
        self.config = config

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email (optional, uses config default if not provided)
            from_name: Sender name (optional)

        Returns:
            Dict with success status and message
        """
        pass

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """
        Test the provider connection/configuration.

        Returns:
            Dict with success status and message
        """
        pass

    def get_from_email(self, from_email: str | None = None) -> str:
        """Get the from email address, using config default if not provided."""
        return from_email or self.config.get("from_email", "")

    def get_from_name(self, from_name: str | None = None) -> str:
        """Get the from name, using config default if not provided."""
        return from_name or self.config.get("from_name", "")
