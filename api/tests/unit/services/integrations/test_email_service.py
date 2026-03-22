from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.integrations.email_service import EmailService


class TestEmailService:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_config_service(self):
        with patch("src.services.integrations.email_service.IntegrationConfigService") as mock:
            mock_instance = mock.return_value
            # Make async methods return AsyncMock
            mock_instance.get_active_config_data = AsyncMock()
            mock_instance.get_config_data = AsyncMock()
            yield mock_instance

    @pytest.fixture
    def email_service(self, mock_db_session, mock_config_service):
        service = EmailService(mock_db_session)
        service.config_service = mock_config_service
        return service

    async def test_send_email_no_config(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = None

        result = await email_service.send_email("test@example.com", "Subject", "Content")

        assert result["success"] is False
        assert "No email configuration found" in result["message"]

    async def test_send_email_exception(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.side_effect = Exception("DB Error")

        result = await email_service.send_email("test@example.com", "Subject", "Content")

        assert result["success"] is False
        assert "Failed to send email" in result["message"]

    async def test_send_email_smtp_success(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "user",
            "smtp_password": "password",
            "from_email": "sender@example.com",
        }

        with patch("smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value

            result = await email_service.send_email(
                "to@example.com", "Subject", "<html>Content</html>", text_content="Plain text"
            )

            assert result["success"] is True
            assert result["provider"] == "smtp"

            mock_smtp.assert_called_with("smtp.example.com", 587, timeout=60)
            instance.starttls.assert_called_once()
            instance.login.assert_called_with("user", "password")
            instance.sendmail.assert_called_once()

    async def test_send_email_smtp_incomplete_config(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.example.com",
            # Missing username/password
        }

        result = await email_service.send_email("to@example.com", "Subject", "Content")

        assert result["success"] is False
        assert "SMTP configuration is incomplete" in result["message"]

    async def test_send_email_smtp_exception(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.example.com",
            "smtp_username": "user",
            "smtp_password": "password",
        }

        with patch("smtplib.SMTP", side_effect=Exception("SMTP Connection Error")):
            result = await email_service.send_email("to@example.com", "Subject", "Content")

            assert result["success"] is False
            assert "SMTP send failed" in result["message"]

    async def test_send_email_smtp_ssl(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_username": "user",
            "smtp_password": "password",
            "use_tls": False,  # Implies SSL
            "from_email": "sender@example.com",
        }

        with patch("src.services.integrations.email_service.smtplib") as mock_smtplib:
            mock_smtp_ssl = mock_smtplib.SMTP_SSL
            instance = mock_smtp_ssl.return_value

            result = await email_service.send_email("to@example.com", "Subject", "<html>Content</html>")

            assert result["success"] is True
            mock_smtp_ssl.assert_called_with("smtp.example.com", 465, timeout=60)
            instance.login.assert_called_with("user", "password")

    async def test_send_email_sendgrid_success(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "sendgrid",
            "credentials": {"api_key": "sg_key"},
            "from_email": "sender@example.com",
        }

        with (
            patch("src.services.integrations.email_service.SendGridAPIClient", create=True) as mock_sg_client,
            patch("src.services.integrations.email_service.SENDGRID_AVAILABLE", True),
            patch("src.services.integrations.email_service.Email", create=True),
            patch("src.services.integrations.email_service.To", create=True),
            patch("src.services.integrations.email_service.Content", create=True),
            patch("src.services.integrations.email_service.Mail", create=True) as mock_mail,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_sg_client.return_value.send.return_value = mock_response

            result = await email_service.send_email(
                "to@example.com", "Subject", "<html>Content</html>", text_content="Plain text"
            )

            assert result["success"] is True
            assert result["provider"] == "sendgrid"
            mock_sg_client.assert_called_with("sg_key")
            # Check if text content was added
            mock_mail.return_value.add_content.assert_called_once()

    async def test_send_email_sendgrid_missing_key(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {"provider": "sendgrid", "api_key": ""}

        with patch("src.services.integrations.email_service.SENDGRID_AVAILABLE", True):
            result = await email_service.send_email("to@example.com", "Subject", "Content")

            assert result["success"] is False
            assert "SendGrid API key is not configured" in result["message"]

    async def test_send_email_sendgrid_exception(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "sendgrid",
            "credentials": {"api_key": "sg_key"},
        }

        with (
            patch("src.services.integrations.email_service.SENDGRID_AVAILABLE", True),
            patch(
                "src.services.integrations.email_service.SendGridAPIClient",
                create=True,
                side_effect=Exception("API Error"),
            ),
        ):
            result = await email_service.send_email("to@example.com", "Subject", "Content")

            assert result["success"] is False
            assert "SendGrid send failed" in result["message"]

    async def test_send_email_sendgrid_missing_library(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {"provider": "sendgrid", "api_key": "sg_key"}

        with patch("src.services.integrations.email_service.SENDGRID_AVAILABLE", False):
            result = await email_service.send_email("to@example.com", "Subject", "Content")

            assert result["success"] is False
            assert "SendGrid library is not installed" in result["message"]

    async def test_send_verification_email(self, email_service):
        with patch.object(email_service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}

            result = await email_service.send_verification_email("test@example.com", "token123")

            assert result["success"] is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[1]["to_email"] == "test@example.com"
            assert "token123" in args[1]["html_content"]

    async def test_send_password_reset_email(self, email_service):
        with patch.object(email_service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}

            result = await email_service.send_password_reset_email("test@example.com", "reset_token")

            assert result["success"] is True
            mock_send.assert_called_once()
            args = mock_send.call_args
            assert args[1]["to_email"] == "test@example.com"
            assert "reset_token" in args[1]["html_content"]

    async def test_test_connection_smtp(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.test",
            "smtp_port": 587,
            "smtp_username": "user",
            "smtp_password": "pass",
        }

        with patch("smtplib.SMTP") as mock_smtp:
            result = await email_service.test_connection()

            assert result["success"] is True
            assert result["message"] == "SMTP connection successful"
            mock_smtp.return_value.login.assert_called_with("user", "pass")
            mock_smtp.return_value.quit.assert_called_once()

    async def test_test_connection_smtp_ssl(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.test",
            "smtp_port": 465,
            "smtp_username": "user",
            "smtp_password": "pass",
            "use_tls": False,
        }

        with patch("src.services.integrations.email_service.smtplib") as mock_smtplib:
            mock_smtp_ssl = mock_smtplib.SMTP_SSL
            result = await email_service.test_connection()

            assert result["success"] is True
            mock_smtp_ssl.assert_called_with("smtp.test", 465, timeout=10)

    async def test_test_connection_incomplete_config(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.test",
            # Missing username/password
        }

        result = await email_service.test_connection()

        assert result["success"] is False
        assert "SMTP configuration is incomplete" in result["message"]

    async def test_test_connection_exception(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.test",
            "smtp_username": "user",
            "smtp_password": "pass",
        }

        with patch("smtplib.SMTP", side_effect=Exception("Connection timeout")):
            result = await email_service.test_connection()

            assert result["success"] is False
            assert "Connection test failed" in result["message"]

    async def test_test_connection_with_id(self, email_service, mock_config_service):
        mock_config_service.get_config_data.return_value = {
            "provider": "smtp",
            "smtp_host": "smtp.test",
            "smtp_username": "user",
            "smtp_password": "pass",
        }

        with patch("smtplib.SMTP"):
            result = await email_service.test_connection(config_id="conf_123")

            assert result["success"] is True
            mock_config_service.get_config_data.assert_called_with("conf_123")

    async def test_test_connection_with_id_not_found(self, email_service, mock_config_service):
        mock_config_service.get_config_data.return_value = None

        result = await email_service.test_connection(config_id="conf_123")

        assert result["success"] is False
        assert "Configuration not found" in result["message"]

    async def test_test_connection_no_active_config(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = None

        result = await email_service.test_connection()

        assert result["success"] is False
        assert "No email configuration found" in result["message"]

    async def test_test_connection_sendgrid_success(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {
            "provider": "sendgrid",
            "credentials": {"api_key": "sg_key"},
        }

        result = await email_service.test_connection()

        assert result["success"] is True
        assert "SendGrid configuration is valid" in result["message"]

    async def test_test_connection_sendgrid_missing_key(self, email_service, mock_config_service):
        mock_config_service.get_active_config_data.return_value = {"provider": "sendgrid", "api_key": ""}

        result = await email_service.test_connection()

        assert result["success"] is False
        assert "SendGrid API key is missing" in result["message"]
