"""
Security utilities for agent management.

Provides encryption and hashing for sensitive data like API keys.
"""

import hashlib
import logging

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manager for securely handling API keys.

    Uses Fernet symmetric encryption to encrypt/decrypt API keys
    and SHA-256 hashing for verification.
    """

    def __init__(self, encryption_key: bytes | None = None):
        """
        Initialize the API key manager.

        Args:
            encryption_key: Fernet encryption key. If None, generates a new key.
        """
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
            logger.warning(
                "No encryption key provided. Generated a new key. "
                "This key should be stored securely and reused across restarts."
            )

        self.cipher = Fernet(encryption_key)
        self.encryption_key = encryption_key

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new Fernet encryption key.

        Returns:
            Encryption key as bytes
        """
        return Fernet.generate_key()

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt an API key for secure storage.

        Args:
            api_key: Plain text API key

        Returns:
            Encrypted API key as base64 string
        """
        if not api_key:
            return ""

        try:
            encrypted = self.cipher.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt an encrypted API key.

        Args:
            encrypted_key: Encrypted API key as base64 string

        Returns:
            Decrypted API key as plain text
        """
        if not encrypted_key:
            return ""

        try:
            decrypted = self.cipher.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Create a SHA-256 hash of an API key for verification.

        This is useful for checking if an API key has changed without
        storing the actual key.

        Args:
            api_key: Plain text API key

        Returns:
            SHA-256 hash as hex string
        """
        if not api_key:
            return ""

        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def verify_api_key(api_key: str, key_hash: str) -> bool:
        """
        Verify an API key against its hash.

        Args:
            api_key: Plain text API key to verify
            key_hash: Expected hash of the API key

        Returns:
            True if the key matches the hash, False otherwise
        """
        if not api_key or not key_hash:
            return False

        return APIKeyManager.hash_api_key(api_key) == key_hash

    def mask_api_key(self, api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes.

        Args:
            api_key: Plain text API key
            visible_chars: Number of characters to show at the end

        Returns:
            Masked API key (e.g., "sk-...xyz123")
        """
        if not api_key:
            return ""

        if len(api_key) <= visible_chars:
            return "*" * len(api_key)

        return f"{'*' * (len(api_key) - visible_chars)}{api_key[-visible_chars:]}"


# Global instance (should be initialized with a persistent key in production)
_api_key_manager: APIKeyManager | None = None


def get_api_key_manager(encryption_key: bytes | None = None) -> APIKeyManager:
    """
    Get or create the global API key manager instance.

    Args:
        encryption_key: Optional encryption key. If provided on first call,
                       will be used to initialize the manager.

    Returns:
        APIKeyManager instance
    """
    global _api_key_manager

    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(encryption_key)

    return _api_key_manager


def set_encryption_key(encryption_key: bytes) -> None:
    """
    Set the encryption key for the global API key manager.

    This should be called once at application startup with a persistent key.

    Args:
        encryption_key: Fernet encryption key
    """
    global _api_key_manager
    _api_key_manager = APIKeyManager(encryption_key)


# Convenience functions for encryption/decryption
def encrypt_value(value: str) -> str:
    """
    Encrypt a value using the encryption key from environment.

    Args:
        value: Plain text value to encrypt

    Returns:
        Encrypted value as base64 string
    """
    import os

    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY not found in environment variables")

    manager = APIKeyManager(encryption_key.encode())
    return manager.encrypt_api_key(value)


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted value using the encryption key from environment.

    Args:
        encrypted_value: Encrypted value as base64 string

    Returns:
        Decrypted value as plain text
    """
    import os

    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY not found in environment variables")

    manager = APIKeyManager(encryption_key.encode())
    return manager.decrypt_api_key(encrypted_value)
