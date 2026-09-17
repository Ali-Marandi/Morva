from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KeyManagementError(RuntimeError):
    """Base error for managed application key handling."""


class UnknownKeyVersionError(KeyManagementError):
    """Raised when ciphertext references an unavailable key version."""


class InvalidKeyMaterialError(KeyManagementError):
    """Raised when managed key material is malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class KeyMaterial:
    version: str
    encryption_key: bytes
    lookup_hmac_key: bytes

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise InvalidKeyMaterialError("key version must not be empty")
        if len(self.encryption_key) != 32:
            raise InvalidKeyMaterialError("field encryption keys must be exactly 32 bytes")
        if len(self.lookup_hmac_key) < 32:
            raise InvalidKeyMaterialError("lookup HMAC keys must be at least 32 bytes")


@dataclass(frozen=True, slots=True)
class ManagedKeyRing:
    """Provider-neutral key ring with one active version and retained decrypt keys."""

    active_version: str
    keys: Mapping[str, KeyMaterial]

    def __post_init__(self) -> None:
        if not self.active_version.strip():
            raise InvalidKeyMaterialError("active key version must not be empty")
        if self.active_version not in self.keys:
            raise InvalidKeyMaterialError("active key version is missing from key ring")
        if len(self.keys) > 32:
            raise InvalidKeyMaterialError("key ring exceeds the supported 32-version retention window")
        for version, key in self.keys.items():
            if version != key.version:
                raise InvalidKeyMaterialError("key-ring version mismatch")

    @property
    def active(self) -> KeyMaterial:
        return self.keys[self.active_version]

    @staticmethod
    def _decode_key(value: str, *, label: str) -> bytes:
        try:
            return base64.urlsafe_b64decode(value.encode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise InvalidKeyMaterialError(f"invalid base64 {label}") from exc

    @classmethod
    def from_environment(
        cls,
        *,
        active_version: str,
        encryption_keys: str,
        lookup_hmac_keys: str,
    ) -> "ManagedKeyRing":
        enc = _parse_versioned_secret_map(encryption_keys, label="field encryption keys")
        hmac_keys = _parse_versioned_secret_map(lookup_hmac_keys, label="lookup HMAC keys")
        if not enc or not hmac_keys:
            raise InvalidKeyMaterialError("both managed key maps are required")
        versions = set(enc) | set(hmac_keys)
        if set(enc) != set(hmac_keys):
            raise InvalidKeyMaterialError("encryption and HMAC key versions must match")
        keys = {
            version: KeyMaterial(
                version=version,
                encryption_key=cls._decode_key(enc[version], label="encryption key"),
                lookup_hmac_key=cls._decode_key(hmac_keys[version], label="lookup HMAC key"),
            )
            for version in versions
        }
        return cls(active_version=active_version, keys=keys)

    def encrypt(self, plaintext: bytes, *, associated_data: bytes = b"") -> str:
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext must be bytes")
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.active.encryption_key).encrypt(nonce, plaintext, associated_data)
        payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii").rstrip("=")
        return f"{self.active_version}.{payload}"

    def decrypt(self, token: str, *, associated_data: bytes = b"") -> bytes:
        try:
            version, payload = token.split(".", 1)
        except ValueError as exc:
            raise KeyManagementError("invalid encrypted value format") from exc
        key = self.keys.get(version)
        if key is None:
            raise UnknownKeyVersionError(f"key version {version!r} is not retained")
        try:
            raw = base64.urlsafe_b64decode((payload + "=" * (-len(payload) % 4)).encode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise KeyManagementError("invalid encrypted value encoding") from exc
        if len(raw) < 12 + 16:
            raise KeyManagementError("encrypted value is too short")
        return AESGCM(key.encryption_key).decrypt(raw[:12], raw[12:], associated_data)

    def lookup_hmac(self, value: str, *, context: str = "") -> str:
        message = f"{context}\x00{value}".encode("utf-8")
        digest = hmac.new(self.active.lookup_hmac_key, message, hashlib.sha256).hexdigest()
        return digest

    def has_version(self, version: str) -> bool:
        return version in self.keys


def _parse_versioned_secret_map(raw: str, *, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            version, value = item.split(":", 1)
        except ValueError as exc:
            raise InvalidKeyMaterialError(f"invalid {label} entry") from exc
        version = version.strip()
        value = value.strip()
        if not version or not value:
            raise InvalidKeyMaterialError(f"invalid {label} entry")
        if version in result:
            raise InvalidKeyMaterialError(f"duplicate {label} version {version}")
        result[version] = value
    return result


def legacy_key_ring(*, key_version: str, encryption_key: str, lookup_hmac_key: str) -> ManagedKeyRing:
    """Build a one-version ring for backward-compatible development and staging configuration."""
    return ManagedKeyRing.from_environment(
        active_version=key_version,
        encryption_keys=f"{key_version}:{encryption_key}",
        lookup_hmac_keys=f"{key_version}:{lookup_hmac_key}",
    )
