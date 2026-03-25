"""
AES-256-GCM: master kalit env dan (32 bayt, base64). Har encrypt — yangi IV va salt.
Kontekst AAD sifatida; boshqa kontekstda decrypt yiqiladi.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass(frozen=True)
class EncryptedBlob:
    ciphertext: bytes
    iv: bytes
    salt: bytes
    tag: bytes

    def to_storage_tuple(self) -> tuple[bytes, bytes, bytes, bytes]:
        return self.ciphertext, self.iv, self.salt, self.tag

    @classmethod
    def from_storage(
        cls,
        ciphertext: bytes,
        iv: bytes,
        salt: bytes,
        tag: bytes,
    ) -> EncryptedBlob:
        return cls(ciphertext=ciphertext, iv=iv, salt=salt, tag=tag)


def build_encryption_service(
    *,
    master_encryption_key_hex: str = "",
    encryption_master_key_b64: str = "",
) -> EncryptionService | None:
    """MASTER_ENCRYPTION_KEY (64 hex) ustuvor; aks holda ENCRYPTION_MASTER_KEY_B64."""
    hx = (master_encryption_key_hex or "").strip()
    if hx:
        if len(hx) < 64:
            raise ValueError("MASTER_ENCRYPTION_KEY kamida 64 ta hex belgi (32 bayt) bo‘lishi kerak")
        return EncryptionService.from_hex_key(hx)
    b64 = (encryption_master_key_b64 or "").strip()
    if b64:
        return EncryptionService.from_base64_key(b64)
    return None


class EncryptionService:
    _KEY_LEN = 32
    _IV_LEN = 12
    _SALT_LEN = 16
    _TAG_LEN = 16
    _PBKDF2_ITERATIONS = 390_000

    def __init__(self, master_key_32: bytes) -> None:
        if len(master_key_32) != self._KEY_LEN:
            raise ValueError(f"Master key must be exactly {self._KEY_LEN} bytes")
        self._master = master_key_32

    @classmethod
    def from_base64_key(cls, b64_key: str) -> EncryptionService:
        raw = base64.b64decode(b64_key.strip(), validate=True)
        return cls(raw)

    @classmethod
    def from_hex_key(cls, hex_key: str) -> EncryptionService:
        raw = bytes.fromhex(hex_key.strip())
        if len(raw) != cls._KEY_LEN:
            raise ValueError(f"Hex kalit aynan {cls._KEY_LEN} bayt (64 hex) bo‘lishi kerak")
        return cls(raw)

    def _derive_aes_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self._KEY_LEN,
            salt=salt,
            iterations=self._PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._master)

    def encrypt(self, plaintext: str, context: str) -> EncryptedBlob:
        if not plaintext:
            raise ValueError("plaintext must be non-empty")
        salt = secrets.token_bytes(self._SALT_LEN)
        iv = secrets.token_bytes(self._IV_LEN)
        aes_key = self._derive_aes_key(salt)
        aes = AESGCM(aes_key)
        aad = context.encode("utf-8")
        pt = plaintext.encode("utf-8")
        ct_and_tag = aes.encrypt(iv, pt, aad)
        tag = ct_and_tag[-self._TAG_LEN :]
        ciphertext = ct_and_tag[: -self._TAG_LEN]
        return EncryptedBlob(ciphertext=ciphertext, iv=iv, salt=salt, tag=tag)

    def decrypt(self, data: EncryptedBlob, context: str) -> str:
        aes_key = self._derive_aes_key(data.salt)
        aes = AESGCM(aes_key)
        aad = context.encode("utf-8")
        payload = data.ciphertext + data.tag
        pt = aes.decrypt(data.iv, payload, aad)
        return pt.decode("utf-8")


def encryption_service_from_env(b64_key: str | None) -> EncryptionService | None:
    if not b64_key or not b64_key.strip():
        return None
    return EncryptionService.from_base64_key(b64_key)
