"""Brevo (formerly Sendinblue) email provider implementation using HTTP API."""

import logging
from typing import Any

import requests

from .base_provider import BaseEmailProvider

logger = logging.getLogger(__name__)

BREVO_API_BASE = "https://api.brevo.com/v3"


class BrevoProvider(BaseEmailProvider):
    """Brevo email provider using REST API (port 443 — no SMTP required)."""

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
        Send an email using Brevo Transactional Email API.

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

            if not api_key:
                logger.error("Brevo API key not configured")
                return {"success": False, "message": "Brevo API key is not configured"}

            from_addr = self.get_from_email(from_email)
            sender_name = self.get_from_name(from_name)

            if not from_addr:
                logger.error("Brevo sender email not configured")
                return {"success": False, "message": "Sender email is not configured"}

            payload: dict[str, Any] = {
                "sender": {"email": from_addr, "name": sender_name} if sender_name else {"email": from_addr},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }

            if text_content:
                payload["textContent"] = text_content

            reply_to = self.config.get("reply_to")
            if reply_to:
                payload["replyTo"] = {"email": reply_to}

            response = requests.post(
                f"{BREVO_API_BASE}/smtp/email",
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                message_id = response.json().get("messageId")
                logger.info(f"Email sent successfully to {to_email} via Brevo. Message ID: {message_id}")
                return {
                    "success": True,
                    "message": "Email sent successfully",
                    "message_id": message_id,
                    "provider": "brevo",
                }

            error_msg = response.text or f"HTTP {response.status_code}"
            logger.error(f"Brevo API returned status {response.status_code}: {error_msg}")
            return {"success": False, "message": f"Brevo API error: {error_msg}", "provider": "brevo"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Brevo API request failed: {str(e)}")
            return {"success": False, "message": f"Brevo API request failed: {str(e)}", "provider": "brevo"}
        except Exception as e:
            logger.error(f"Failed to send email via Brevo: {str(e)}")
            return {"success": False, "message": f"Failed to send email: {str(e)}", "provider": "brevo"}

    def test_connection(self) -> dict[str, Any]:
        """
        Test the Brevo API connection by fetching account info.

        Returns:
            Dict with success status and message
        """
        try:
            api_key = self.config.get("api_key")

            if not api_key:
                return {"success": False, "message": "Brevo API key is required"}

            response = requests.get(
                f"{BREVO_API_BASE}/account",
                headers={"api-key": api_key},
                timeout=10,
            )

            if response.status_code == 200:
                account = response.json()
                email = account.get("email", "")
                logger.info(f"Brevo connection test successful for account: {email}")
                return {"success": True, "message": f"Connection successful. Account: {email}"}
            elif response.status_code == 401:
                return {"success": False, "message": "Authentication failed — check your API key"}
            else:
                error_msg = response.text or f"HTTP {response.status_code}"
                return {"success": False, "message": f"Connection test failed: {error_msg}"}

        except requests.exceptions.RequestException as e:
            logger.error(f"Brevo connection test failed: {str(e)}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Brevo connection test error: {str(e)}")
            return {"success": False, "message": f"Connection test error: {str(e)}"}
