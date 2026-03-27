"""Unit tests for SMTPProvider."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.services.integrations.providers.smtp_provider import SMTPProvider


def _config(**kwargs):
    base = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password": "secret",
        "from_email": "sender@example.com",
        "from_name": "Test Sender",
        "use_tls": True,
        "use_ssl": False,
    }
    base.update(kwargs)
    return base


@pytest.mark.unit
class TestSendEmailSuccess:
    def test_returns_success_true(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config())
            result = provider.send_email("to@example.com", "Subject", "<p>Hello</p>")

        assert result["success"] is True

    def test_returns_success_message(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value = MagicMock()
            provider = SMTPProvider(_config())
            result = provider.send_email("to@example.com", "Sub", "<b>Hi</b>")
        assert "success" in result["message"].lower()

    def test_calls_sendmail_with_correct_recipient(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config())
            provider.send_email("recipient@example.com", "Sub", "<p>body</p>")

        mock_server.sendmail.assert_called_once()
        _, to_arg, _ = mock_server.sendmail.call_args[0]
        assert to_arg == "recipient@example.com"

    def test_calls_starttls_when_use_tls_true(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config(use_tls=True, use_ssl=False))
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_server.starttls.assert_called_once()

    def test_does_not_call_starttls_when_use_tls_false(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config(use_tls=False, use_ssl=False))
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_server.starttls.assert_not_called()

    def test_uses_smtp_ssl_when_use_ssl_true(self):
        with patch("smtplib.SMTP_SSL") as mock_ssl_cls:
            mock_server = MagicMock()
            mock_ssl_cls.return_value = mock_server

            provider = SMTPProvider(_config(use_ssl=True))
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_ssl_cls.assert_called_once()

    def test_logs_in_with_credentials(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config(username="user", password="pass"))
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_server.login.assert_called_once_with("user", "pass")

    def test_skips_login_when_no_credentials(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            config = _config()
            config.pop("username")
            config.pop("password")
            provider = SMTPProvider(config)
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_server.login.assert_not_called()

    def test_calls_quit_after_send(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config())
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        mock_server.quit.assert_called()

    def test_includes_text_content_when_provided(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config())
            provider.send_email("to@example.com", "Sub", "<p>html</p>", text_content="plain text")

        # sendmail is called — message content tested via call args
        _, _, message_str = mock_server.sendmail.call_args[0]
        assert "plain text" in message_str

    def test_from_name_included_in_from_header(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config(from_name="Alice"))
            provider.send_email("to@example.com", "Sub", "<p>body</p>")

        _, _, message_str = mock_server.sendmail.call_args[0]
        assert "Alice" in message_str


@pytest.mark.unit
class TestSendEmailFailure:
    def test_returns_success_false_on_smtp_error(self):
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connect failed")):
            provider = SMTPProvider(_config())
            result = provider.send_email("to@example.com", "Sub", "<p>body</p>")
        assert result["success"] is False

    def test_error_message_describes_failure(self):
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("auth error")):
            provider = SMTPProvider(_config())
            result = provider.send_email("to@example.com", "Sub", "<p>body</p>")
        assert "Failed" in result["message"]

    def test_quit_called_on_sendmail_error(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_server.sendmail.side_effect = smtplib.SMTPException("send failed")
            mock_smtp_cls.return_value = mock_server

            provider = SMTPProvider(_config())
            result = provider.send_email("to@example.com", "Sub", "<p>body</p>")

        # quit() called in cleanup path
        mock_server.quit.assert_called()
        assert result["success"] is False


@pytest.mark.unit
class TestTestConnection:
    def test_returns_success_true_on_valid_connection(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value = MagicMock()
            provider = SMTPProvider(_config())
            result = provider.test_connection()
        assert result["success"] is True

    def test_uses_smtp_ssl_for_ssl_config(self):
        with patch("smtplib.SMTP_SSL") as mock_ssl_cls:
            mock_ssl_cls.return_value = MagicMock()
            provider = SMTPProvider(_config(use_ssl=True))
            result = provider.test_connection()
        mock_ssl_cls.assert_called_once()
        assert result["success"] is True

    def test_returns_success_false_on_connection_error(self):
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
            provider = SMTPProvider(_config())
            result = provider.test_connection()
        assert result["success"] is False

    def test_error_message_describes_failure(self):
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPAuthenticationError(535, b"auth failed")):
            provider = SMTPProvider(_config())
            result = provider.test_connection()
        assert result["success"] is False
        assert "Connection failed" in result["message"]

    def test_logs_in_during_connection_test(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server
            provider = SMTPProvider(_config(username="u", password="p"))
            provider.test_connection()
        mock_server.login.assert_called_once_with("u", "p")

    def test_calls_starttls_in_connection_test(self):
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value = mock_server
            provider = SMTPProvider(_config(use_tls=True, use_ssl=False))
            provider.test_connection()
        mock_server.starttls.assert_called_once()


@pytest.mark.unit
class TestBaseProviderHelpers:
    def test_get_from_email_uses_arg_when_provided(self):
        provider = SMTPProvider(_config(from_email="default@example.com"))
        assert provider.get_from_email("override@example.com") == "override@example.com"

    def test_get_from_email_falls_back_to_config(self):
        provider = SMTPProvider(_config(from_email="default@example.com"))
        assert provider.get_from_email(None) == "default@example.com"

    def test_get_from_name_uses_arg_when_provided(self):
        provider = SMTPProvider(_config(from_name="Default"))
        assert provider.get_from_name("Override") == "Override"

    def test_get_from_name_falls_back_to_config(self):
        provider = SMTPProvider(_config(from_name="Config Name"))
        assert provider.get_from_name(None) == "Config Name"
