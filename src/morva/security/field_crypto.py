from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldCryptoError(ValueError):
    pass


def _key(material: str) -> bytes:
    if not material:
        raise FieldCryptoError("field encryption key is not configured")
    return hashlib.sha256(material.encode("utf-8")).digest()


def encrypt(value: str, *, key_material: str) -> str:
    key = _key(key_material)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt(token: str, *, key_material: str) -> str:
    key = _key(key_material)
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(raw) < 13:
            raise FieldCryptoError("invalid encrypted field")
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8")
    except Exception as exc:
        raise FieldCryptoError("unable to decrypt field") from exc


def lookup_hmac(value: str, *, key_material: str) -> str:
    if not key_material:
        raise FieldCryptoError("lookup HMAC key is not configured")
    return hmac.new(key_material.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
