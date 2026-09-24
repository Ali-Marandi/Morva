from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class FieldCryptoError(ValueError):
    pass


_LEGACY_KEY_VERSION = "v1"
_CURRENT_KEY_VERSION = "v2"
_KEY_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
_HKDF_SALT = b"morva-field-crypto-hkdf-v2"
_HKDF_INFO_PREFIX = b"morva/field-crypto/key/"


def _validate_key_version(key_version: str) -> str:
    if not isinstance(key_version, str) or not _KEY_VERSION_RE.fullmatch(key_version):
        raise FieldCryptoError("invalid field encryption key version")
    return key_version


def _legacy_key(material: str) -> bytes:
    if not material:
        raise FieldCryptoError("field encryption key is not configured")
    return hashlib.sha256(material.encode("utf-8")).digest()


def _key(material: str, key_version: str = _CURRENT_KEY_VERSION) -> bytes:
    if not material:
        raise FieldCryptoError("field encryption key is not configured")
    version = _validate_key_version(key_version)
    if version == _LEGACY_KEY_VERSION:
        return _legacy_key(material)
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO_PREFIX + version.encode("ascii"),
    ).derive(material.encode("utf-8"))


def encrypt(value: str, *, key_material: str, key_version: str = _CURRENT_KEY_VERSION) -> str:
    """Encrypt with versioned HKDF-derived AES-256-GCM.

    key_material must be a high-entropy managed secret. It must never be a
    user-supplied password or other low-entropy credential.
    """
    version = _validate_key_version(key_version)
    key = _key(key_material, version)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), None)
    encoded = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{version}.{encoded}"


def decrypt(
    token: str,
    *,
    key_material: str,
    key_version: str | None = None,
) -> str:
    """Decrypt HKDF ciphertext or legacy unversioned SHA-256 ciphertext.

    Existing values without a v<version>. prefix use the legacy derivation so
    key rotation does not invalidate stored data. Re-encryption with encrypt()
    migrates values to the current format.
    """
    try:
        encoded = token
        if "." in token:
            prefix, encoded = token.split(".", 1)
            embedded_version = _validate_key_version(prefix[1:])
            if key_version is not None and _validate_key_version(key_version) != embedded_version:
                raise FieldCryptoError("field encryption key version mismatch")
            key = _key(key_material, embedded_version)
        else:
            if key_version not in (None, _LEGACY_KEY_VERSION):
                raise FieldCryptoError("legacy ciphertext requires key version v1")
            key = _legacy_key(key_material)
        raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
        if len(raw) < 13:
            raise FieldCryptoError("invalid encrypted field")
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8")
    except FieldCryptoError:
        raise
    except Exception as exc:
        raise FieldCryptoError("unable to decrypt field") from exc


def lookup_hmac(value: str, *, key_material: str) -> str:
    if not key_material:
        raise FieldCryptoError("lookup HMAC key is not configured")
    return hmac.new(key_material.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
