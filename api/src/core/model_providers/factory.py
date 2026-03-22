"""
Model provider factory.

Creates and manages model provider instances.
"""

from src.core.errors import ValidationError

from .anthropic_provider import AnthropicProvider
from .base import BaseModelProvider, ModelProviderType
from .openai_provider import OpenAIProvider


class ModelProviderFactory:
    """
    Factory for creating model provider instances.

    This factory manages the creation of different model providers
    and ensures proper configuration.
    """

    _providers: dict[ModelProviderType, type[BaseModelProvider]] = {
        ModelProviderType.OPENAI: OpenAIProvider,
        ModelProviderType.ANTHROPIC: AnthropicProvider,
    }

    @classmethod
    def create(
        cls,
        provider_type: ModelProviderType,
        api_key: str,
        **kwargs,
    ) -> BaseModelProvider:
        """
        Create a model provider instance.

        Args:
            provider_type: Type of provider to create
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration

        Returns:
            Provider instance

        Raises:
            ValidationError: If provider type is not supported
        """
        provider_class = cls._providers.get(provider_type)

        if not provider_class:
            raise ValidationError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {', '.join(p.value for p in cls._providers)}"
            )

        return provider_class(api_key=api_key, **kwargs)

    @classmethod
    def create_from_config(
        cls,
        config: dict,
    ) -> BaseModelProvider:
        """
        Create a provider from configuration dict.

        Args:
            config: Configuration dictionary with keys:
                - provider: Provider type string
                - api_key: API key
                - Additional provider-specific config

        Returns:
            Provider instance

        Raises:
            ValidationError: If configuration is invalid
        """
        if "provider" not in config:
            raise ValidationError("Provider type not specified in config")

        if "api_key" not in config:
            raise ValidationError("API key not specified in config")

        try:
            provider_type = ModelProviderType(config["provider"])
        except ValueError as e:
            raise ValidationError(f"Invalid provider type: {config['provider']}") from e

        # Extract provider-specific config
        provider_config = {k: v for k, v in config.items() if k not in ("provider", "api_key")}

        return cls.create(
            provider_type=provider_type,
            api_key=config["api_key"],
            **provider_config,
        )

    @classmethod
    def register_provider(
        cls,
        provider_type: ModelProviderType,
        provider_class: type[BaseModelProvider],
    ) -> None:
        """
        Register a new provider type.

        This allows for dynamic registration of custom providers.

        Args:
            provider_type: Provider type identifier
            provider_class: Provider class to register
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        Get list of supported provider types.

        Returns:
            List of provider type strings
        """
        return [p.value for p in cls._providers]

    @classmethod
    async def validate_provider_config(
        cls,
        provider_type: ModelProviderType,
        api_key: str,
        **kwargs,
    ) -> bool:
        """
        Validate provider configuration by testing credentials.

        Args:
            provider_type: Provider type
            api_key: API key
            **kwargs: Additional configuration

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If provider type is not supported
        """
        provider = cls.create(provider_type, api_key, **kwargs)
        return await provider.validate_credentials()
