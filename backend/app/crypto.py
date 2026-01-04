"""Crypto helpers for encrypting sensitive values at rest."""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet

from app.config import Settings


class CryptoError(RuntimeError):
    """Raised when crypto operations fail."""


@dataclass(frozen=True)
class CryptoProvider:
    """Interface for encrypt/decrypt operations."""

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt plaintext into ciphertext bytes."""
        raise NotImplementedError

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes into plaintext."""
        raise NotImplementedError


class LocalDevCrypto(CryptoProvider):
    """Local dev crypto using a symmetric Fernet key from ENCRYPTION_KEY."""

    def __init__(self, encryption_key: str) -> None:
        if not encryption_key:
            raise CryptoError("ENCRYPTION_KEY is required for LocalDevCrypto")
        self._fernet = Fernet(encryption_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        return self._fernet.decrypt(ciphertext).decode("utf-8")


class GcpKmsCrypto(CryptoProvider):
    """Stub for a GCP KMS-backed crypto implementation."""

    def __init__(self, key_resource_id: str) -> None:
        self._key_resource_id = key_resource_id

    def encrypt(self, plaintext: str) -> bytes:
        raise NotImplementedError("GcpKmsCrypto is not implemented in local dev")

    def decrypt(self, ciphertext: bytes) -> str:
        raise NotImplementedError("GcpKmsCrypto is not implemented in local dev")


def get_crypto(settings: Settings) -> CryptoProvider:
    """Return a crypto provider for the current environment."""
    return LocalDevCrypto(settings.encryption_key)
