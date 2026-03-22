"""Tests for SendGridProvider."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.integrations.providers.sendgrid_provider import SendGridProvider


@pytest.fixture
def sendgrid_config():
    """Create SendGrid configuration."""
    return {
        "api_key": "test_api_key",
        "from_email": "noreply@example.com",
        "from_name": "Test Sender",
        "reply_to": "support@example.com",
    }


@pytest.fixture
def sendgrid_provider(sendgrid_config):
    """Create SendGridProvider instance."""
    return SendGridProvider(sendgrid_config)


class TestSendEmail:
    """Tests for send_email method."""

    def test_send_email_success(self, sendgrid_provider):
        """Test successfully sending email."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 202
            mock_response.headers = {"X-Message-Id": "msg_123"}

            mock_client = Mock()
            mock_client.send.return_value = mock_response
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.send_email(
                to_email="test@example.com", subject="Test Subject", html_content="<p>Test Content</p>"
            )

            assert result["success"] is True
            assert result["message"] == "Email sent successfully"
            assert result["message_id"] == "msg_123"
            mock_client.send.assert_called_once()

    def test_send_email_with_text_content(self, sendgrid_provider):
        """Test sending email with text content."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}

            mock_client = Mock()
            mock_client.send.return_value = mock_response
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.send_email(
                to_email="test@example.com", subject="Test", html_content="<p>HTML</p>", text_content="Plain text"
            )

            assert result["success"] is True

    def test_send_email_with_custom_from(self, sendgrid_provider):
        """Test sending email with custom from address."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_response = Mock()
            mock_response.status_code = 202
            mock_response.headers = {}

            mock_client = Mock()
            mock_client.send.return_value = mock_response
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.send_email(
                to_email="test@example.com",
                subject="Test",
                html_content="<p>Test</p>",
                from_email="custom@example.com",
                from_name="Custom Sender",
            )

            assert result["success"] is True

    def test_send_email_api_error(self, sendgrid_provider):
        """Test handling API error."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_response = Mock()
            mock_response.status_code = 400

            mock_client = Mock()
            mock_client.send.return_value = mock_response
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.send_email(
                to_email="test@example.com", subject="Test", html_content="<p>Test</p>"
            )

            assert result["success"] is False
            assert "400" in result["message"]

    def test_send_email_import_error(self, sendgrid_provider):
        """Test handling ImportError."""
        with patch.dict("sys.modules", {"sendgrid": None}):
            result = sendgrid_provider.send_email(
                to_email="test@example.com", subject="Test", html_content="<p>Test</p>"
            )

            assert result["success"] is False
            assert "not installed" in result["message"] or "Failed to send" in result["message"]

    def test_send_email_exception(self, sendgrid_provider):
        """Test handling general exception."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_client = Mock()
            mock_client.send.side_effect = Exception("API Error")
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.send_email(
                to_email="test@example.com", subject="Test", html_content="<p>Test</p>"
            )

            assert result["success"] is False
            assert "API Error" in result["message"]


class TestTestConnection:
    """Tests for test_connection method."""

    def test_test_connection_success(self, sendgrid_provider):
        """Test successful connection test."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_response = Mock()
            mock_response.status_code = 200

            # Mock the fluent API chain: sg.client.api_keys._(key_id).get()
            mock_underscore = Mock()
            mock_underscore.get.return_value = mock_response

            mock_api_keys = Mock()
            mock_api_keys._ = Mock(return_value=mock_underscore)

            mock_client_attr = Mock()
            mock_client_attr.api_keys = mock_api_keys

            mock_client = Mock()
            mock_client.client = mock_client_attr
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.test_connection()

            assert result["success"] is True
            assert result["message"] == "Connection successful"

    def test_test_connection_no_api_key(self):
        """Test connection test without API key."""
        provider = SendGridProvider({})
        result = provider.test_connection()

        assert result["success"] is False
        assert "required" in result["message"].lower()

    def test_test_connection_api_error(self, sendgrid_provider):
        """Test connection test with API error."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_response = Mock()
            mock_response.status_code = 401

            mock_client = Mock()
            mock_client.client.api_keys.return_value.get.return_value = mock_response
            mock_sg_client.return_value = mock_client

            result = sendgrid_provider.test_connection()

            assert result["success"] is False

    def test_test_connection_import_error(self, sendgrid_provider):
        """Test connection test with ImportError."""
        with patch.dict("sys.modules", {"sendgrid": None}):
            result = sendgrid_provider.test_connection()

            assert result["success"] is False
            assert "not installed" in result["message"] or "failed" in result["message"].lower()

    def test_test_connection_exception(self, sendgrid_provider):
        """Test connection test with exception."""
        with patch("sendgrid.SendGridAPIClient") as mock_sg_client:
            mock_sg_client.side_effect = Exception("Connection error")

            result = sendgrid_provider.test_connection()

            assert result["success"] is False
            assert "Connection error" in result["message"]
