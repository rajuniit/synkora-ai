"""Unit tests for APIKeyManager (agents/security.py)."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from src.services.agents.security import APIKeyManager, get_api_key_manager, set_encryption_key


@pytest.fixture
def key():
    return Fernet.generate_key()


@pytest.fixture
def manager(key):
    return APIKeyManager(encryption_key=key)


@pytest.mark.unit
class TestEncryptDecrypt:
    def test_encrypt_returns_non_empty_string(self, manager):
        result = manager.encrypt_api_key("sk-test-1234")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decrypt_recovers_original(self, manager):
        original = "sk-anthropic-abcdef"
        encrypted = manager.encrypt_api_key(original)
        assert manager.decrypt_api_key(encrypted) == original

    def test_encrypt_empty_returns_empty(self, manager):
        assert manager.encrypt_api_key("") == ""

    def test_decrypt_empty_returns_empty(self, manager):
        assert manager.decrypt_api_key("") == ""

    def test_encrypt_produces_different_ciphertext_each_time(self, manager):
        # Fernet uses a random IV, so same plaintext → different ciphertext
        enc1 = manager.encrypt_api_key("same-key")
        enc2 = manager.encrypt_api_key("same-key")
        assert enc1 != enc2

    def test_decrypt_with_wrong_key_raises(self, key):
        manager1 = APIKeyManager(encryption_key=key)
        manager2 = APIKeyManager(encryption_key=Fernet.generate_key())
        encrypted = manager1.encrypt_api_key("secret")
        with pytest.raises(InvalidToken):
            manager2.decrypt_api_key(encrypted)


@pytest.mark.unit
class TestHashAndVerify:
    def test_hash_returns_64_char_hex(self):
        result = APIKeyManager.hash_api_key("test-key")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_empty_returns_empty(self):
        assert APIKeyManager.hash_api_key("") == ""

    def test_verify_correct_key_returns_true(self):
        key_val = "sk-verify-test"
        h = APIKeyManager.hash_api_key(key_val)
        assert APIKeyManager.verify_api_key(key_val, h) is True

    def test_verify_wrong_key_returns_false(self):
        h = APIKeyManager.hash_api_key("correct-key")
        assert APIKeyManager.verify_api_key("wrong-key", h) is False

    def test_verify_empty_api_key_returns_false(self):
        h = APIKeyManager.hash_api_key("some-key")
        assert APIKeyManager.verify_api_key("", h) is False

    def test_verify_empty_hash_returns_false(self):
        assert APIKeyManager.verify_api_key("some-key", "") is False

    def test_hash_deterministic(self):
        assert APIKeyManager.hash_api_key("abc") == APIKeyManager.hash_api_key("abc")


@pytest.mark.unit
class TestMaskApiKey:
    def test_masks_all_but_last_four(self, manager):
        result = manager.mask_api_key("sk-abcdefgh1234")
        assert result.endswith("1234")
        assert "*" in result

    def test_short_key_fully_masked(self, manager):
        result = manager.mask_api_key("abc")
        assert result == "***"

    def test_empty_key_returns_empty(self, manager):
        assert manager.mask_api_key("") == ""

    def test_custom_visible_chars(self, manager):
        result = manager.mask_api_key("sk-secretxyz789", visible_chars=6)
        assert result.endswith("xyz789")


@pytest.mark.unit
class TestGenerateKey:
    def test_generate_key_returns_bytes(self):
        key = APIKeyManager.generate_key()
        assert isinstance(key, bytes)

    def test_generated_keys_are_unique(self):
        assert APIKeyManager.generate_key() != APIKeyManager.generate_key()


@pytest.mark.unit
class TestGlobalManager:
    def teardown_method(self):
        # Reset global state
        import src.services.agents.security as mod

        mod._api_key_manager = None

    def test_get_creates_singleton(self):
        import src.services.agents.security as mod

        mod._api_key_manager = None
        m1 = get_api_key_manager()
        m2 = get_api_key_manager()
        assert m1 is m2

    def test_set_encryption_key_replaces_manager(self):
        import src.services.agents.security as mod

        mod._api_key_manager = None
        key = Fernet.generate_key()
        set_encryption_key(key)
        assert mod._api_key_manager is not None
        assert mod._api_key_manager.encryption_key == key


@pytest.mark.unit
class TestEncryptDecryptValueFunctions:
    def test_encrypt_value_requires_env_var(self, monkeypatch):
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        from src.services.agents.security import encrypt_value

        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            encrypt_value("test")

    def test_decrypt_value_requires_env_var(self, monkeypatch):
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        from src.services.agents.security import decrypt_value

        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            decrypt_value("enc")

    def test_encrypt_decrypt_value_roundtrip(self, monkeypatch):
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        from src.services.agents.security import decrypt_value, encrypt_value

        plaintext = "my-secret-value"
        encrypted = encrypt_value(plaintext)
        assert decrypt_value(encrypted) == plaintext
