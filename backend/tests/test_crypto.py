"""Tests for crypto helpers."""

from cryptography.fernet import Fernet

from app.crypto import LocalDevCrypto


def test_local_dev_crypto_roundtrip() -> None:
    key = Fernet.generate_key().decode("utf-8")
    crypto = LocalDevCrypto(key)
    ciphertext = crypto.encrypt("hello")
    assert crypto.decrypt(ciphertext) == "hello"
