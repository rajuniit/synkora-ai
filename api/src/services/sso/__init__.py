"""
SSO (Single Sign-On) Services.

This package provides SSO authentication services for enterprise identity providers.
"""

from .okta_sso import OktaSSOService

__all__ = ["OktaSSOService"]
