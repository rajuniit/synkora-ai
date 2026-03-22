"""Tests for SMTPProvider."""

import smtplib
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.integrations.providers.smtp_provider import SMTPProvider


@pytest.fixture
def smtp_config():
    """Create SMTP configuration."""
    return {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "password": "test_password",
        "use_tls": True,
        "use_ssl": False,
        "from_email": "noreply@example.com",
        "from_name": "Test Sender",
    }


@pytest.fixture
def smtp_provider(smtp_config):
    """Create SMTPProvider instance."""
    return SMTPProvider(smtp_config)


class TestSendEmail:
    """Tests for send_email method."""

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp, smtp_provider):
        """Test successfully sending email."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = smtp_provider.send_email(
            to_email="test@example.com", subject="Test Subject", html_content="<p>Test Content</p>"
        )

        assert result["success"] is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_with_text_content(self, mock_smtp, smtp_provider):
        """Test sending email with text content."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = smtp_provider.send_email(
            to_email="test@example.com", subject="Test", html_content="<p>HTML</p>", text_content="Plain text"
        )

        assert result["success"] is True
        mock_server.sendmail.assert_called_once()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP_SSL")
    def test_send_email_with_ssl(self, mock_smtp_ssl):
        """Test sending email with SSL."""
        config = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "test@example.com",
            "password": "password",
            "use_ssl": True,
            "from_email": "noreply@example.com",
        }
        provider = SMTPProvider(config)

        mock_server = Mock()
        mock_smtp_ssl.return_value = mock_server

        result = provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is True
        mock_smtp_ssl.assert_called_once()
        # Should NOT call starttls when using SSL
        mock_server.starttls.assert_not_called()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_without_auth(self, mock_smtp):
        """Test sending email without authentication."""
        config = {"host": "smtp.example.com", "port": 25, "use_tls": False, "from_email": "noreply@example.com"}
        provider = SMTPProvider(config)

        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is True
        mock_server.login.assert_not_called()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_with_custom_from(self, mock_smtp, smtp_provider):
        """Test sending email with custom from."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = smtp_provider.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Test</p>",
            from_email="custom@example.com",
            from_name="Custom Sender",
        )

        assert result["success"] is True

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_smtp_exception(self, mock_smtp, smtp_provider):
        """Test handling SMTP exception."""
        mock_server = Mock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("SMTP Error")
        mock_smtp.return_value = mock_server

        result = smtp_provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert "SMTP Error" in result["message"]
        # Verify cleanup was attempted
        mock_server.quit.assert_called()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_connection_error(self, mock_smtp, smtp_provider):
        """Test handling connection error."""
        mock_smtp.side_effect = ConnectionError("Cannot connect")

        result = smtp_provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert "Cannot connect" in result["message"]

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_send_email_timeout(self, mock_smtp):
        """Test handling timeout."""
        config = {"host": "smtp.example.com", "port": 587, "timeout": 5, "from_email": "noreply@example.com"}
        provider = SMTPProvider(config)

        mock_smtp.side_effect = TimeoutError("Connection timeout")

        result = provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False


class TestTestConnection:
    """Tests for test_connection method."""

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_test_connection_success(self, mock_smtp, smtp_provider):
        """Test successful connection test."""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = smtp_provider.test_connection()

        assert result["success"] is True
        assert result["message"] == "Connection successful"
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP_SSL")
    def test_test_connection_with_ssl(self, mock_smtp_ssl):
        """Test connection test with SSL."""
        config = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "test@example.com",
            "password": "password",
            "use_ssl": True,
            "from_email": "noreply@example.com",
        }
        provider = SMTPProvider(config)

        mock_server = Mock()
        mock_smtp_ssl.return_value = mock_server

        result = provider.test_connection()

        assert result["success"] is True
        mock_smtp_ssl.assert_called_once()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_test_connection_without_auth(self, mock_smtp):
        """Test connection test without authentication."""
        config = {"host": "smtp.example.com", "port": 25, "use_tls": False, "from_email": "noreply@example.com"}
        provider = SMTPProvider(config)

        mock_server = Mock()
        mock_smtp.return_value = mock_server

        result = provider.test_connection()

        assert result["success"] is True
        mock_server.login.assert_not_called()

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_test_connection_auth_failed(self, mock_smtp, smtp_provider):
        """Test connection test with authentication failure."""
        mock_server = Mock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
        mock_smtp.return_value = mock_server

        result = smtp_provider.test_connection()

        assert result["success"] is False
        assert "Authentication failed" in result["message"]

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_test_connection_timeout(self, mock_smtp, smtp_provider):
        """Test connection test with timeout."""
        mock_smtp.side_effect = TimeoutError("Connection timeout")

        result = smtp_provider.test_connection()

        assert result["success"] is False
        assert "Connection timeout" in result["message"]

    @patch("src.services.integrations.providers.smtp_provider.smtplib.SMTP")
    def test_test_connection_general_exception(self, mock_smtp, smtp_provider):
        """Test connection test with general exception."""
        mock_smtp.side_effect = Exception("Unexpected error")

        result = smtp_provider.test_connection()

        assert result["success"] is False
        assert "Unexpected error" in result["message"]
