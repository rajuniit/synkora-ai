"""Mailgun email provider implementation."""

import logging
from typing import Any

import requests

from .base_provider import BaseEmailProvider

logger = logging.getLogger(__name__)

MAILGUN_API_BASE = "https://api.mailgun.net/v3"


class MailgunProvider(BaseEmailProvider):
    """Mailgun email provider implementation using REST API."""

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
        Send an email using Mailgun API.

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
            api_key = self.config.get("api_key")
            domain = self.config.get("domain")

            if not api_key:
                logger.error("Mailgun API key not configured")
                return {"success": False, "message": "Mailgun API key is not configured"}

            if not domain:
                logger.error("Mailgun domain not configured")
                return {"success": False, "message": "Mailgun domain is not configured"}

            from_addr = self.get_from_email(from_email)
            sender_name = self.get_from_name(from_name)

            # Format from address with optional name
            if sender_name:
                from_formatted = f"{sender_name} <{from_addr}>"
            else:
                from_formatted = from_addr

            # Prepare Mailgun API request
            api_url = f"{MAILGUN_API_BASE}/{domain}/messages"

            data = {
                "from": from_formatted,
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }

            # Add text content if provided
            if text_content:
                data["text"] = text_content

            # Add reply-to if configured
            reply_to = self.config.get("reply_to")
            if reply_to:
                data["h:Reply-To"] = reply_to

            # Send request to Mailgun API
            response = requests.post(api_url, auth=("api", api_key), data=data, timeout=30)

            if response.status_code in [200, 201]:
                response_data = response.json()
                message_id = response_data.get("id")
                logger.info(f"Email sent successfully to {to_email} via Mailgun. Message ID: {message_id}")
                return {
                    "success": True,
                    "message": "Email sent successfully",
                    "message_id": message_id,
                    "provider": "mailgun",
                }
            else:
                error_msg = response.text or f"HTTP {response.status_code}"
                logger.error(f"Mailgun API returned status {response.status_code}: {error_msg}")
                return {
                    "success": False,
                    "message": f"Mailgun API error: {error_msg}",
                    "status_code": response.status_code,
                    "provider": "mailgun",
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Mailgun API request failed: {str(e)}")
            return {"success": False, "message": f"Mailgun API request failed: {str(e)}", "provider": "mailgun"}
        except Exception as e:
            logger.error(f"Failed to send email via Mailgun: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}", "provider": "mailgun"}

    def test_connection(self) -> dict[str, Any]:
        """
        Test the Mailgun API connection.

        Returns:
            Dict with success status and message
        """
        try:
            api_key = self.config.get("api_key")
            domain = self.config.get("domain")

            if not api_key:
                return {"success": False, "message": "Mailgun API key is required"}

            if not domain:
                return {"success": False, "message": "Mailgun domain is required"}

            # Test API key by getting domain info (lightweight call)
            api_url = f"{MAILGUN_API_BASE}/domains/{domain}"

            response = requests.get(api_url, auth=("api", api_key), timeout=10)

            if response.status_code == 200:
                domain_info = response.json()
                logger.info(f"Mailgun connection test successful for domain: {domain}")
                return {
                    "success": True,
                    "message": f"Connection successful for domain: {domain}",
                    "domain": domain_info.get("domain", {}).get("name"),
                }
            elif response.status_code == 401:
                logger.error("Mailgun authentication failed - invalid API key")
                return {"success": False, "message": "Authentication failed - check your API key"}
            elif response.status_code == 404:
                logger.error(f"Mailgun domain not found: {domain}")
                return {"success": False, "message": f"Domain not found: {domain}"}
            else:
                error_msg = response.text or f"HTTP {response.status_code}"
                logger.error(f"Mailgun test returned status {response.status_code}: {error_msg}")
                return {"success": False, "message": f"Connection test failed: {error_msg}"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Mailgun connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Mailgun connection test error: {str(e)}")
            return {"success": False, "message": f"Connection test error: {str(e)}"}
