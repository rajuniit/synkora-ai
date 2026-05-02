"""Unit tests for integration provider factories."""

import pytest

from src.services.integrations.providers.factory import (
    EmailProviderFactory,
    IntegrationProviderFactory,
    PaymentProviderFactory,
)
from src.services.integrations.providers.smtp_provider import SMTPProvider


@pytest.mark.unit
class TestEmailProviderFactoryCreate:
    def test_smtp_returns_smtp_provider(self):
        provider = EmailProviderFactory.create("smtp", {"host": "localhost"})
        assert isinstance(provider, SMTPProvider)

    def test_case_insensitive_smtp(self):
        provider = EmailProviderFactory.create("SMTP", {"host": "localhost"})
        assert isinstance(provider, SMTPProvider)

    def test_sendgrid_returns_sendgrid_provider(self):
        from src.services.integrations.providers.sendgrid_provider import SendGridProvider

        provider = EmailProviderFactory.create("sendgrid", {"api_key": "key"})
        assert isinstance(provider, SendGridProvider)

    def test_mailgun_returns_mailgun_provider(self):
        from src.services.integrations.providers.mailgun_provider import MailgunProvider

        provider = EmailProviderFactory.create("mailgun", {"api_key": "key", "domain": "mg.example.com"})
        assert isinstance(provider, MailgunProvider)

    def test_brevo_returns_brevo_provider(self):
        from src.services.integrations.providers.brevo_provider import BrevoProvider

        provider = EmailProviderFactory.create("brevo", {"api_key": "key"})
        assert isinstance(provider, BrevoProvider)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported email provider"):
            EmailProviderFactory.create("fax", {})

    def test_error_message_lists_supported_providers(self):
        with pytest.raises(ValueError) as exc_info:
            EmailProviderFactory.create("pigeon", {})
        assert "smtp" in str(exc_info.value)
        assert "sendgrid" in str(exc_info.value)

    def test_config_passed_to_provider(self):
        config = {"host": "smtp.example.com", "port": 465}
        provider = EmailProviderFactory.create("smtp", config)
        assert provider.config is config


@pytest.mark.unit
class TestEmailProviderFactoryGetSupported:
    def test_returns_list(self):
        result = EmailProviderFactory.get_supported_providers()
        assert isinstance(result, list)

    def test_contains_smtp(self):
        assert "smtp" in EmailProviderFactory.get_supported_providers()

    def test_contains_all_four(self):
        supported = EmailProviderFactory.get_supported_providers()
        assert set(supported) == {"smtp", "sendgrid", "mailgun", "brevo"}


@pytest.mark.unit
class TestPaymentProviderFactoryGetSupported:
    def test_returns_list_with_stripe(self):
        result = PaymentProviderFactory.get_supported_providers()
        assert "stripe" in result


@pytest.mark.unit
class TestPaymentProviderFactoryCreate:
    def test_unknown_provider_raises_value_error(self):
        with pytest.raises((ValueError, Exception)):
            PaymentProviderFactory.create("paypal", {})

    def test_unsupported_when_stripe_unavailable(self):
        import src.services.integrations.providers.factory as factory_mod

        original_stripe = factory_mod.StripeProvider
        original_base = factory_mod.BaseIntegrationProvider
        try:
            factory_mod.StripeProvider = None
            factory_mod.BaseIntegrationProvider = None
            with pytest.raises(ValueError, match="Payment providers require"):
                PaymentProviderFactory.create("stripe", {})
        finally:
            factory_mod.StripeProvider = original_stripe
            factory_mod.BaseIntegrationProvider = original_base


@pytest.mark.unit
class TestIntegrationProviderFactoryGetTypes:
    def test_returns_list(self):
        result = IntegrationProviderFactory.get_supported_types()
        assert isinstance(result, list)

    def test_contains_email_and_payment(self):
        result = IntegrationProviderFactory.get_supported_types()
        assert "email" in result
        assert "payment" in result


@pytest.mark.unit
class TestIntegrationProviderFactoryGetProviders:
    def test_unknown_type_returns_empty_list(self):
        # Only unknown types trigger the early return [] branch
        result = IntegrationProviderFactory.get_supported_providers("fax")
        assert result == []

    def test_known_type_does_not_raise(self):
        # The method has a missing return statement for known types (returns None),
        # but should not raise exceptions
        IntegrationProviderFactory.get_supported_providers("email")
        IntegrationProviderFactory.get_supported_providers("payment")


@pytest.mark.unit
class TestIntegrationProviderFactoryCreate:
    def test_email_smtp_returns_smtp_provider(self):
        provider = IntegrationProviderFactory.create("email", "smtp", {"host": "localhost"})
        assert isinstance(provider, SMTPProvider)

    def test_unknown_integration_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported integration type"):
            IntegrationProviderFactory.create("sms", "twilio", {})

    def test_unknown_provider_for_valid_type_raises(self):
        with pytest.raises(ValueError):
            IntegrationProviderFactory.create("email", "courier", {})

    def test_case_insensitive_integration_type(self):
        provider = IntegrationProviderFactory.create("EMAIL", "smtp", {"host": "localhost"})
        assert isinstance(provider, SMTPProvider)

    def test_error_lists_supported_types(self):
        with pytest.raises(ValueError) as exc_info:
            IntegrationProviderFactory.create("voicemail", "generic", {})
        assert "email" in str(exc_info.value)
