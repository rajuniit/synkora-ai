"""Patch the onelogin SAML library before any test imports it.

The xmlsec/lxml native library version mismatch on this machine prevents
importing onelogin.saml2 directly, so we stub the entire package.
"""

import sys
from unittest.mock import MagicMock

# Stub the whole onelogin stack so importing okta_sso doesn't crash.
for mod in [
    "onelogin",
    "onelogin.saml2",
    "onelogin.saml2.auth",
    "onelogin.saml2.settings",
    "onelogin.saml2.utils",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

# Make OneLogin_Saml2_Auth accessible as an attribute on the stub module.
sys.modules["onelogin.saml2.auth"].OneLogin_Saml2_Auth = MagicMock()
