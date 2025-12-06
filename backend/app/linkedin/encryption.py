"""AES encryption service for password storage (Single Responsibility)."""

import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.linkedin.interfaces import IEncryptionService


class AESEncryptionService(IEncryptionService):
    """AES-256 encryption service using CBC mode with PKCS7 padding."""

    BLOCK_SIZE = 16  # AES block size in bytes
    KEY_SIZE = 32  # AES-256 key size in bytes

    def __init__(self, secret_key: str) -> None:
        """Initialize with a secret key (will be padded/truncated to 32 bytes)."""
        self._key = self._normalize_key(secret_key)

    def _normalize_key(self, key: str) -> bytes:
        """Normalize key to exactly 32 bytes."""
        key_bytes = key.encode("utf-8")
        if len(key_bytes) < self.KEY_SIZE:
            # Pad with zeros
            key_bytes = key_bytes + b"\0" * (self.KEY_SIZE - len(key_bytes))
        elif len(key_bytes) > self.KEY_SIZE:
            # Truncate
            key_bytes = key_bytes[: self.KEY_SIZE]
        return key_bytes

    def _pad(self, data: bytes) -> bytes:
        """Apply PKCS7 padding."""
        padding_length = self.BLOCK_SIZE - (len(data) % self.BLOCK_SIZE)
        return data + bytes([padding_length] * padding_length)

    def _unpad(self, data: bytes) -> bytes:
        """Remove PKCS7 padding."""
        padding_length = data[-1]
        return data[:-padding_length]

    def encrypt(self, plain_text: str) -> str:
        """Encrypt plain text using AES-256-CBC."""
        # Generate random IV
        iv = os.urandom(self.BLOCK_SIZE)

        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Pad and encrypt
        padded_data = self._pad(plain_text.encode("utf-8"))
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV + encrypted data and encode as base64
        combined = iv + encrypted_data
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt AES-256-CBC encrypted text."""
        # Decode from base64
        combined = base64.b64decode(encrypted_text.encode("utf-8"))

        # Extract IV and encrypted data
        iv = combined[: self.BLOCK_SIZE]
        encrypted_data = combined[self.BLOCK_SIZE :]

        # Create cipher
        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Decrypt and unpad
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        data = self._unpad(padded_data)

        return data.decode("utf-8")
