from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class TrustedKeyRegistryError(ValueError):
    """Raised when a trusted signing-key registry is invalid or rejects a key."""


@dataclass(frozen=True, slots=True)
class TrustedSigningKey:
    key_id: str
    public_key_sha256: str
    status: str
    valid_from: datetime
    valid_until: datetime | None = None
    replacement_key_id: str | None = None

    def __post_init__(self) -> None:
        if not self.key_id.strip():
            raise TrustedKeyRegistryError("key_id is required")
        if len(self.public_key_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.public_key_sha256.lower()
        ):
            raise TrustedKeyRegistryError("public_key_sha256 must be a SHA-256 hex digest")
        if self.status not in {"active", "retired", "revoked"}:
            raise TrustedKeyRegistryError("unsupported trusted-key status")
        if self.valid_from.tzinfo is None:
            raise TrustedKeyRegistryError("valid_from must be timezone-aware")
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise TrustedKeyRegistryError("valid_until must be timezone-aware")
            if self.valid_until < self.valid_from:
                raise TrustedKeyRegistryError("valid_until cannot precede valid_from")
        if self.replacement_key_id == self.key_id:
            raise TrustedKeyRegistryError("replacement key cannot equal the current key")


@dataclass(frozen=True, slots=True)
class TrustedKeyRegistry:
    registry_id: str
    version: int
    keys: tuple[TrustedSigningKey, ...]

    def __post_init__(self) -> None:
        if not self.registry_id.strip():
            raise TrustedKeyRegistryError("registry_id is required")
        if self.version < 1:
            raise TrustedKeyRegistryError("registry version must be positive")
        key_ids = tuple(item.key_id for item in self.keys)
        if len(key_ids) != len(set(key_ids)):
            raise TrustedKeyRegistryError("trusted key IDs must be unique")
        if not self.keys:
            raise TrustedKeyRegistryError("at least one trusted signing key is required")
        known = set(key_ids)
        for item in self.keys:
            if item.replacement_key_id is not None and item.replacement_key_id not in known:
                raise TrustedKeyRegistryError(
                    "replacement_key_id must reference a registered key"
                )

    @property
    def fingerprint(self) -> str:
        payload = {
            "registry_id": self.registry_id,
            "version": self.version,
            "keys": tuple(
                (
                    item.key_id,
                    item.public_key_sha256.lower(),
                    item.status,
                    item.valid_from.isoformat(),
                    item.valid_until.isoformat() if item.valid_until else None,
                    item.replacement_key_id,
                )
                for item in self.keys
            ),
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def key(self, key_id: str) -> TrustedSigningKey:
        for item in self.keys:
            if item.key_id == key_id:
                return item
        raise TrustedKeyRegistryError("signing key is not registered")

    @staticmethod
    def key_id_for(public_key: Ed25519PublicKey) -> str:
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return sha256(raw).hexdigest()

    @staticmethod
    def public_key_sha256_for(public_key: Ed25519PublicKey) -> str:
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return sha256(raw).hexdigest()

    def assert_trusted(
        self,
        key_id: str,
        public_key: Ed25519PublicKey,
        verified_at: datetime,
    ) -> None:
        if verified_at.tzinfo is None:
            raise TrustedKeyRegistryError("verified_at must be timezone-aware")
        record = self.key(key_id)
        if self.key_id_for(public_key) != record.key_id:
            raise TrustedKeyRegistryError("public key does not match registered key_id")
        if self.public_key_sha256_for(public_key) != record.public_key_sha256.lower():
            raise TrustedKeyRegistryError("public key hash does not match trusted registry")
        if record.status != "active":
            raise TrustedKeyRegistryError(f"signing key is {record.status}")
        if verified_at < record.valid_from:
            raise TrustedKeyRegistryError("signing key is not yet valid")
        if record.valid_until is not None and verified_at > record.valid_until:
            raise TrustedKeyRegistryError("signing key validity has expired")

    def add_key(self, key: TrustedSigningKey) -> "TrustedKeyRegistry":
        if any(item.key_id == key.key_id for item in self.keys):
            raise TrustedKeyRegistryError("signing key is already registered")
        return TrustedKeyRegistry(self.registry_id, self.version + 1, self.keys + (key,))

    def rotate_key(
        self,
        current_key_id: str,
        replacement: TrustedSigningKey,
    ) -> "TrustedKeyRegistry":
        current = self.key(current_key_id)
        if current.status != "active":
            raise TrustedKeyRegistryError("only an active key can be rotated")
        if any(item.key_id == replacement.key_id for item in self.keys):
            raise TrustedKeyRegistryError("replacement signing key is already registered")
        if replacement.status != "active":
            raise TrustedKeyRegistryError("replacement signing key must be active")
        retired = TrustedSigningKey(
            key_id=current.key_id,
            public_key_sha256=current.public_key_sha256,
            status="retired",
            valid_from=current.valid_from,
            valid_until=current.valid_until,
            replacement_key_id=replacement.key_id,
        )
        keys = tuple(
            retired if item.key_id == current_key_id else item for item in self.keys
        ) + (replacement,)
        return TrustedKeyRegistry(self.registry_id, self.version + 1, keys)

    def revoke_key(self, key_id: str) -> "TrustedKeyRegistry":
        record = self.key(key_id)
        if record.status == "revoked":
            return self
        revoked = TrustedSigningKey(
            key_id=record.key_id,
            public_key_sha256=record.public_key_sha256,
            status="revoked",
            valid_from=record.valid_from,
            valid_until=record.valid_until,
            replacement_key_id=record.replacement_key_id,
        )
        return TrustedKeyRegistry(
            self.registry_id,
            self.version + 1,
            tuple(revoked if item.key_id == key_id else item for item in self.keys),
        )
