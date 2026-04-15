"""
Stripe Payment Provider

Handles Stripe payment integration configuration and operations.
"""


import stripe

from .base_provider import BaseIntegrationProvider


class StripeProvider(BaseIntegrationProvider):
    """Stripe payment provider implementation"""

    def __init__(self, config: dict):
        """
        Initialize Stripe provider with configuration

        Args:
            config: Provider configuration containing credentials and settings
        """
        super().__init__(config)
        self._initialize_stripe()

    def _initialize_stripe(self):
        """Initialize Stripe SDK with API key"""
        secret_key = self.get_credential("secret_key")
        if secret_key:
            stripe.api_key = secret_key
        else:
            raise ValueError("Stripe secret key not found in configuration")

    def validate_config(self) -> bool:
        """
        Validate Stripe configuration

        Returns:
            True if configuration is valid
        """
        required_credentials = ["secret_key", "webhook_secret"]
        required_settings = ["publishable_key"]

        # Check required credentials
        for cred in required_credentials:
            if not self.get_credential(cred):
                raise ValueError(f"Missing required credential: {cred}")

        # Check required settings
        for setting in required_settings:
            if not self.get_setting(setting):
                raise ValueError(f"Missing required setting: {setting}")

        return True

    def test_connection(self) -> dict:
        """
        Test Stripe connection by making a simple API call

        Returns:
            Dict with success status and message
        """
        try:
            # Try to retrieve account information
            account = stripe.Account.retrieve()

            return {
                "success": True,
                "message": f"Successfully connected to Stripe account: {account.id}",
                "details": {
                    "account_id": account.id,
                    "email": account.email,
                    "country": account.country,
                    "charges_enabled": account.charges_enabled,
                    "payouts_enabled": account.payouts_enabled,
                },
            }
        except stripe.error.AuthenticationError:
            return {"success": False, "message": "Invalid Stripe API key", "error": "Authentication failed"}
        except stripe.error.StripeError as e:
            return {"success": False, "message": f"Stripe API error: {str(e)}", "error": str(e)}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}", "error": str(e)}

    def get_secret_key(self) -> str | None:
        """Get Stripe secret key"""
        return self.get_credential("secret_key")

    def get_publishable_key(self) -> str | None:
        """Get Stripe publishable key"""
        return self.get_setting("publishable_key")

    def get_webhook_secret(self) -> str | None:
        """Get Stripe webhook secret"""
        return self.get_credential("webhook_secret")

    def is_enabled(self) -> bool:
        """Check if Stripe integration is enabled"""
        return self.get_setting("enabled", True)

    @staticmethod
    def get_config_schema() -> dict:
        """
        Get configuration schema for Stripe provider

        Returns:
            Dict describing the configuration structure
        """
        return {
            "credentials": {
                "secret_key": {
                    "type": "string",
                    "required": True,
                    "encrypted": True,
                    "description": "Stripe secret key (sk_...)",
                    "placeholder": "sk_test_...",
                },
                "webhook_secret": {
                    "type": "string",
                    "required": True,
                    "encrypted": True,
                    "description": "Stripe webhook signing secret",
                    "placeholder": "whsec_...",
                },
            },
            "settings": {
                "publishable_key": {
                    "type": "string",
                    "required": True,
                    "description": "Stripe publishable key (pk_...)",
                    "placeholder": "pk_test_...",
                },
                "enabled": {
                    "type": "boolean",
                    "required": False,
                    "default": True,
                    "description": "Enable/disable Stripe integration",
                },
            },
            "metadata": {
                "description": {"type": "string", "required": False, "description": "Configuration description"},
                "environment": {
                    "type": "string",
                    "required": False,
                    "description": "Environment (test/production)",
                    "enum": ["test", "production"],
                },
            },
        }
