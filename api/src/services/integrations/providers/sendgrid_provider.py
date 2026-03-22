"""SendGrid email provider implementation."""

import logging
from typing import Any

from .base_provider import BaseEmailProvider

logger = logging.getLogger(__name__)


class SendGridProvider(BaseEmailProvider):
    """SendGrid email provider implementation."""

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
        Send an email using SendGrid API.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email (optional)
            from_name: Sender name (optional)

        Returns:
            Dict with success status and message
        """
        try:
            # Import SendGrid here to make it optional
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Content, Email, Mail, To

            api_key = self.config.get("api_key")
            from_addr = self.get_from_email(from_email)
            sender_name = self.get_from_name(from_name)
            reply_to = self.config.get("reply_to")

            # Create from email object
            from_email_obj = Email(from_addr, sender_name if sender_name else None)

            # Create to email object
            to_email_obj = To(to_email)

            # Create content
            content = Content("text/html", html_content)

            # Create mail object
            mail = Mail(from_email=from_email_obj, to_emails=to_email_obj, subject=subject, html_content=content)

            # Add plain text content if provided
            if text_content:
                mail.add_content(Content("text/plain", text_content))

            # Add reply-to if configured
            if reply_to:
                mail.reply_to = reply_to

            # Send email
            sg = SendGridAPIClient(api_key)
            response = sg.send(mail)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email} via SendGrid")
                return {
                    "success": True,
                    "message": "Email sent successfully",
                    "message_id": response.headers.get("X-Message-Id"),
                }
            else:
                logger.error(f"SendGrid returned status {response.status_code}")
                return {"success": False, "message": f"SendGrid returned status {response.status_code}"}

        except ImportError:
            logger.error("SendGrid library not installed")
            return {"success": False, "message": "SendGrid library not installed. Install with: pip install sendgrid"}
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}

    def test_connection(self) -> dict[str, Any]:
        """
        Test the SendGrid API connection.

        Returns:
            Dict with success status and message
        """
        try:
            # Import SendGrid here to make it optional
            from sendgrid import SendGridAPIClient

            api_key = self.config.get("api_key")

            if not api_key:
                return {"success": False, "message": "API key is required"}

            # Test API key by making a simple API call
            sg = SendGridAPIClient(api_key)

            # Try to get API key permissions (lightweight call)
            response = sg.client.api_keys._(api_key.split(".")[-1]).get()

            if response.status_code == 200:
                logger.info("SendGrid connection test successful")
                return {"success": True, "message": "Connection successful"}
            else:
                logger.error(f"SendGrid test returned status {response.status_code}")
                return {"success": False, "message": f"Connection test failed with status {response.status_code}"}

        except ImportError:
            logger.error("SendGrid library not installed")
            return {"success": False, "message": "SendGrid library not installed. Install with: pip install sendgrid"}
        except Exception as e:
            logger.error(f"SendGrid connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}
