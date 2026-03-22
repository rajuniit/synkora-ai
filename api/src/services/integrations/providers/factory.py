"""Provider factory for creating integration provider instances."""

import logging
from typing import Any

from .base_provider import BaseEmailProvider
from .brevo_provider import BrevoProvider
from .mailgun_provider import MailgunProvider
from .sendgrid_provider import SendGridProvider
from .smtp_provider import SMTPProvider

# Lazy import for payment providers to avoid circular dependencies
try:
    from .base_provider import BaseIntegrationProvider
    from .stripe_provider import StripeProvider
except ImportError:
    BaseIntegrationProvider = None
    StripeProvider = None

logger = logging.getLogger(__name__)


class EmailProviderFactory:
    """Factory for creating email provider instances."""

    @staticmethod
    def create(provider: str, config: dict[str, Any]) -> BaseEmailProvider:
        """
        Create an email provider instance based on the provider type.

        Args:
            provider: Provider type ('smtp', 'sendgrid', etc.)
            config: Provider configuration dictionary

        Returns:
            BaseEmailProvider instance

        Raises:
            ValueError: If provider type is not supported
        """
        providers = {
            "smtp": SMTPProvider,
            "sendgrid": SendGridProvider,
            "mailgun": MailgunProvider,
            "brevo": BrevoProvider,
        }

        provider_class = providers.get(provider.lower())

        if not provider_class:
            supported = ", ".join(providers.keys())
            raise ValueError(f"Unsupported email provider: {provider}. Supported providers: {supported}")

        logger.info(f"Creating {provider} email provider")
        return provider_class(config)

    @staticmethod
    def get_supported_providers() -> list:
        """
        Get list of supported email providers.

        Returns:
            List of supported provider names
        """
        return ["smtp", "sendgrid", "mailgun", "brevo"]


class PaymentProviderFactory:
    """Factory for creating payment provider instances."""

    @staticmethod
    def create(provider: str, config: dict[str, Any]):
        """
        Create a payment provider instance based on the provider type.

        Args:
            provider: Provider type ('stripe', 'paypal', etc.)
            config: Provider configuration dictionary

        Returns:
            Provider instance

        Raises:
            ValueError: If provider type is not supported or BaseIntegrationProvider is not available
        """
        if BaseIntegrationProvider is None or StripeProvider is None:
            raise ValueError(
                "Payment providers require BaseIntegrationProvider. This may not be available in all environments."
            )

        providers = {
            "stripe": StripeProvider,
        }

        provider_class = providers.get(provider.lower())

        if not provider_class:
            supported = ", ".join(providers.keys())
            raise ValueError(f"Unsupported payment provider: {provider}. Supported providers: {supported}")

        logger.info(f"Creating {provider} payment provider")
        return provider_class(config)

    @staticmethod
    def get_supported_providers() -> list:
        """
        Get list of supported payment providers.

        Returns:
            List of supported provider names
        """
        return ["stripe"]


class IntegrationProviderFactory:
    """Main factory for creating any integration provider."""

    @staticmethod
    def create(integration_type: str, provider: str, config: dict[str, Any]):
        """
        Create an integration provider instance.

        Args:
            integration_type: Type of integration ('email', 'payment', etc.)
            provider: Provider name ('smtp', 'stripe', etc.)
            config: Provider configuration dictionary

        Returns:
            Provider instance

        Raises:
            ValueError: If integration type or provider is not supported
        """
        factories = {
            "email": EmailProviderFactory,
            "payment": PaymentProviderFactory,
        }

        factory = factories.get(integration_type.lower())

        if not factory:
            supported = ", ".join(factories.keys())
            raise ValueError(f"Unsupported integration type: {integration_type}. Supported types: {supported}")

        return factory.create(provider, config)

    @staticmethod
    def get_supported_types() -> list:
        """
        Get list of supported integration types.

        Returns:
            List of supported integration type names
        """
        return ["email", "payment"]

    @staticmethod
    def get_supported_providers(integration_type: str) -> list:
        """
        Get list of supported providers for an integration type.

        Args:
            integration_type: Type of integration

        Returns:
            List of supported provider names
        """
        factories = {
            "email": EmailProviderFactory,
            "payment": PaymentProviderFactory,
        }

        factory = factories.get(integration_type.lower())
        if not factory:
            return []
