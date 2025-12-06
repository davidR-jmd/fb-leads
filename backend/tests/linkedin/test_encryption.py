"""Tests for encryption service (TDD - tests first)."""

import pytest

from app.linkedin.encryption import AESEncryptionService


class TestAESEncryptionService:
    """Test AES encryption service."""

    def test_encrypt_returns_different_from_plain_text(self):
        """Encrypted text should be different from plain text."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "my-password"

        encrypted = service.encrypt(plain_text)

        assert encrypted != plain_text

    def test_decrypt_returns_original_text(self):
        """Decrypted text should match original plain text."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "my-password"

        encrypted = service.encrypt(plain_text)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plain_text

    def test_encrypt_produces_different_output_each_time(self):
        """Each encryption should produce different output (due to IV)."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "my-password"

        encrypted1 = service.encrypt(plain_text)
        encrypted2 = service.encrypt(plain_text)

        assert encrypted1 != encrypted2

    def test_decrypt_works_with_different_encryptions(self):
        """Both different encryptions should decrypt to same value."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "my-password"

        encrypted1 = service.encrypt(plain_text)
        encrypted2 = service.encrypt(plain_text)

        assert service.decrypt(encrypted1) == plain_text
        assert service.decrypt(encrypted2) == plain_text

    def test_encrypt_empty_string(self):
        """Should handle empty string."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")

        encrypted = service.encrypt("")
        decrypted = service.decrypt(encrypted)

        assert decrypted == ""

    def test_encrypt_special_characters(self):
        """Should handle special characters."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "p@$$w0rd!#%^&*()_+-=[]{}|;':\",./<>?"

        encrypted = service.encrypt(plain_text)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plain_text

    def test_encrypt_unicode(self):
        """Should handle unicode characters."""
        service = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        plain_text = "mot de passe français 日本語"

        encrypted = service.encrypt(plain_text)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plain_text

    def test_different_keys_produce_different_encryptions(self):
        """Different keys should produce different encryptions."""
        service1 = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        service2 = AESEncryptionService(secret_key="another-key-that-is-32-chars-!!")
        plain_text = "my-password"

        encrypted1 = service1.encrypt(plain_text)
        encrypted2 = service2.encrypt(plain_text)

        assert encrypted1 != encrypted2

    def test_cannot_decrypt_with_wrong_key(self):
        """Decryption with wrong key should fail or produce wrong result."""
        service1 = AESEncryptionService(secret_key="test-secret-key-32-chars-long!!")
        service2 = AESEncryptionService(secret_key="another-key-that-is-32-chars-!!")
        plain_text = "my-password"

        encrypted = service1.encrypt(plain_text)

        # Wrong key should either raise exception or produce different output
        try:
            decrypted = service2.decrypt(encrypted)
            # If no exception, result must be different from original
            assert decrypted != plain_text
        except Exception:
            # Exception is acceptable behavior
            pass

    def test_short_key_is_padded(self):
        """Short keys should be padded to 32 bytes."""
        service = AESEncryptionService(secret_key="short")
        plain_text = "my-password"

        encrypted = service.encrypt(plain_text)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plain_text
