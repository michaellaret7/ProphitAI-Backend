"""Tests for Fernet-based message encryption utilities.

Validates encrypt/decrypt roundtrips, ciphertext uniqueness, error handling
for invalid tokens, and behaviour when the encryption key is missing.
"""

import pytest

import prophitai_data.internal.encryption as enc_mod
from prophitai_data.internal.encryption import encrypt_message, decrypt_message


class TestEncryptDecryptRoundtrip:
    """Basic roundtrip: encrypt then decrypt returns the original content."""

    def test_basic_string(self):
        """A plain ASCII string survives encrypt -> decrypt."""
        plaintext = "Hello, ProphitAI!"
        ciphertext = encrypt_message(plaintext)
        assert decrypt_message(ciphertext) == plaintext

    def test_empty_string(self):
        """An empty string survives encrypt -> decrypt."""
        ciphertext = encrypt_message("")
        assert decrypt_message(ciphertext) == ""

    def test_unicode_content(self):
        """Unicode characters (Japanese + emoji) survive encrypt -> decrypt."""
        plaintext = "ポートフォリオ分析 📈🚀"
        ciphertext = encrypt_message(plaintext)
        assert decrypt_message(ciphertext) == plaintext


class TestCiphertextUniqueness:
    """Fernet uses a random IV, so identical plaintext produces different ciphertext."""

    def test_different_messages_different_ciphertext(self):
        """Two distinct messages must produce different ciphertext."""
        ct1 = encrypt_message("message_one")
        ct2 = encrypt_message("message_two")
        assert ct1 != ct2

    def test_same_message_different_ciphertext(self):
        """The same message encrypted twice should differ (random IV)."""
        ct1 = encrypt_message("same")
        ct2 = encrypt_message("same")
        # Reason: Fernet prepends a random 128-bit IV; collisions are negligible
        assert ct1 != ct2


class TestDecryptInvalid:
    """decrypt_message returns a placeholder for garbage ciphertext."""

    def test_garbage_returns_placeholder(self):
        """Non-Fernet input triggers the InvalidToken fallback."""
        result = decrypt_message("not-a-valid-fernet-token!!!")
        assert result == "[Unable to decrypt message]"


class TestMissingKey:
    """ValueError is raised when MESSAGE_ENCRYPTION_KEY is absent."""

    def test_missing_key_raises(self, monkeypatch):
        """Removing the env var and resetting the cipher must raise ValueError."""
        monkeypatch.delenv("MESSAGE_ENCRYPTION_KEY", raising=False)
        # Reason: force the lazy singleton to re-initialise without a key
        enc_mod._cipher = None

        with pytest.raises(ValueError, match="MESSAGE_ENCRYPTION_KEY"):
            encrypt_message("should fail")

        # Reason: restore cipher singleton so subsequent tests aren't affected
        enc_mod._cipher = None
