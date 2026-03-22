"""SMTP email provider implementation."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from .base_provider import BaseEmailProvider

logger = logging.getLogger(__name__)


class SMTPProvider(BaseEmailProvider):
    """SMTP email provider implementation."""

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
        Send an email using SMTP.

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
            # Get configuration
            host = self.config.get("host")
            port = self.config.get("port", 587)
            username = self.config.get("username")
            password = self.config.get("password")
            use_tls = self.config.get("use_tls", True)
            use_ssl = self.config.get("use_ssl", False)

            from_addr = self.get_from_email(from_email)
            sender_name = self.get_from_name(from_name)

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{from_addr}>" if sender_name else from_addr
            msg["To"] = to_email

            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, "plain")
                msg.attach(part1)

            part2 = MIMEText(html_content, "html")
            msg.attach(part2)

            # Connect and send with timeout to prevent hanging
            # Default timeout: 30 seconds
            smtp_timeout = self.config.get("timeout", 30)
            server = None

            try:
                if use_ssl:
                    server = smtplib.SMTP_SSL(host, port, timeout=smtp_timeout)
                else:
                    server = smtplib.SMTP(host, port, timeout=smtp_timeout)
                    if use_tls:
                        server.starttls()

                if username and password:
                    server.login(username, password)

                server.sendmail(from_addr, to_email, msg.as_string())
                server.quit()
            except Exception as smtp_error:
                # Ensure connection is closed even on error
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass  # Ignore errors during cleanup
                raise smtp_error

            logger.info(f"Email sent successfully to {to_email}")
            return {"success": True, "message": "Email sent successfully"}

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}

    def test_connection(self) -> dict[str, Any]:
        """
        Test the SMTP connection.

        Returns:
            Dict with success status and message
        """
        try:
            host = self.config.get("host")
            port = self.config.get("port", 587)
            username = self.config.get("username")
            password = self.config.get("password")
            use_tls = self.config.get("use_tls", True)
            use_ssl = self.config.get("use_ssl", False)

            # Test connection
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)
                if use_tls:
                    server.starttls()

            if username and password:
                server.login(username, password)

            server.quit()

            logger.info("SMTP connection test successful")
            return {"success": True, "message": "Connection successful"}

        except Exception as e:
            logger.error(f"SMTP connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection failed: {str(e)}"}
