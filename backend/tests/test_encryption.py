from __future__ import annotations

import base64
import secrets

import pytest

from app.services.encryption_service import EncryptionService


def _key_b64() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def test_encrypt_decrypt_roundtrip() -> None:
    enc = EncryptionService.from_base64_key(_key_b64())
    blob = enc.encrypt("maxfiy-matn", "ctx:user:1:ssh:prod")
    assert enc.decrypt(blob, "ctx:user:1:ssh:prod") == "maxfiy-matn"


def test_decrypt_wrong_context_fails() -> None:
    enc = EncryptionService.from_base64_key(_key_b64())
    blob = enc.encrypt("data", "ctx:a")
    with pytest.raises(Exception):
        enc.decrypt(blob, "ctx:b")


def test_invalid_key_length() -> None:
    short = base64.b64encode(b"x" * 16).decode("ascii")
    with pytest.raises(ValueError):
        EncryptionService.from_base64_key(short)
