"""Tests for MailgunProvider."""

from unittest.mock import Mock, patch

import pytest

from src.services.integrations.providers.mailgun_provider import MailgunProvider


@pytest.fixture
def mailgun_config():
    """Create Mailgun configuration."""
    return {
        "api_key": "test_api_key",
        "domain": "example.com",
        "from_email": "noreply@example.com",
        "from_name": "Test Sender",
        "reply_to": "support@example.com",
    }


@pytest.fixture
def mailgun_provider(mailgun_config):
    """Create MailgunProvider instance."""
    return MailgunProvider(mailgun_config)


class TestSendEmail:
    """Tests for send_email method."""

    @patch("src.services.integrations.providers.mailgun_provider.requests.post")
    def test_send_email_success(self, mock_post, mailgun_provider):
        """Test successfully sending email."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_response

        result = mailgun_provider.send_email(
            to_email="test@example.com", subject="Test Subject", html_content="<p>Test Content</p>"
        )

        assert result["success"] is True
        assert result["message_id"] == "msg_123"
        assert result["provider"] == "mailgun"
        mock_post.assert_called_once()

    @patch("src.services.integrations.providers.mailgun_provider.requests.post")
    def test_send_email_with_text_content(self, mock_post, mailgun_provider):
        """Test sending email with text content."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "msg_456"}
        mock_post.return_value = mock_response

        result = mailgun_provider.send_email(
            to_email="test@example.com", subject="Test", html_content="<p>HTML</p>", text_content="Plain text"
        )

        assert result["success"] is True
        # Verify text was included in data
        call_args = mock_post.call_args
        assert "text" in call_args.kwargs["data"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.post")
    def test_send_email_with_custom_from(self, mock_post, mailgun_provider):
        """Test sending email with custom from."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_789"}
        mock_post.return_value = mock_response

        result = mailgun_provider.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Test</p>",
            from_email="custom@example.com",
            from_name="Custom Sender",
        )

        assert result["success"] is True

    def test_send_email_no_api_key(self):
        """Test sending email without API key."""
        provider = MailgunProvider({"domain": "test.com"})
        result = provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert "API key" in result["message"]

    def test_send_email_no_domain(self):
        """Test sending email without domain."""
        provider = MailgunProvider({"api_key": "test_key"})
        result = provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert "domain" in result["message"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.post")
    def test_send_email_api_error(self, mock_post, mailgun_provider):
        """Test handling API error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        result = mailgun_provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert result["status_code"] == 400
        assert "Bad request" in result["message"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.post")
    def test_send_email_request_exception(self, mock_post, mailgun_provider):
        """Test handling request exception."""
        import requests

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = mailgun_provider.send_email(to_email="test@example.com", subject="Test", html_content="<p>Test</p>")

        assert result["success"] is False
        assert "Network error" in result["message"]


class TestTestConnection:
    """Tests for test_connection method."""

    @patch("src.services.integrations.providers.mailgun_provider.requests.get")
    def test_test_connection_success(self, mock_get, mailgun_provider):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"domain": {"name": "example.com"}}
        mock_get.return_value = mock_response

        result = mailgun_provider.test_connection()

        assert result["success"] is True
        assert "domain" in result

    def test_test_connection_no_api_key(self):
        """Test connection test without API key."""
        provider = MailgunProvider({"domain": "test.com"})
        result = provider.test_connection()

        assert result["success"] is False
        assert "API key" in result["message"]

    def test_test_connection_no_domain(self):
        """Test connection test without domain."""
        provider = MailgunProvider({"api_key": "test_key"})
        result = provider.test_connection()

        assert result["success"] is False
        assert "domain" in result["message"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.get")
    def test_test_connection_auth_failed(self, mock_get, mailgun_provider):
        """Test connection test with authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = mailgun_provider.test_connection()

        assert result["success"] is False
        assert "Authentication" in result["message"] or "API key" in result["message"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.get")
    def test_test_connection_domain_not_found(self, mock_get, mailgun_provider):
        """Test connection test with domain not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = mailgun_provider.test_connection()

        assert result["success"] is False
        assert "not found" in result["message"]

    @patch("src.services.integrations.providers.mailgun_provider.requests.get")
    def test_test_connection_request_exception(self, mock_get, mailgun_provider):
        """Test connection test with request exception."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection timeout")

        result = mailgun_provider.test_connection()

        assert result["success"] is False
        assert "Connection timeout" in result["message"]
