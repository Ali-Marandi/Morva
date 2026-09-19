from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .signed_trusted_key_registry import SignedTrustedKeyRegistry


class RootRotationError(ValueError):
    """Raised when a root trust-anchor transition is invalid."""


@dataclass(frozen=True, slots=True)
class RootRotationCeremony:
    ceremony_id: str
    registry_id: str
    from_version: int
    to_version: int
    old_root_key_id: str
    new_root_key_id: str
    effective_at: datetime
    transition_kind: str
    old_root_action: str
    previous_registry_fingerprint: str
    new_registry_fingerprint: str
    old_root_signature_b64: str
    new_root_signature_b64: str

    def __post_init__(self) -> None:
        if not self.ceremony_id.strip() or not self.registry_id.strip():
            raise RootRotationError("ceremony_id and registry_id are required")
        if self.from_version < 1 or self.to_version != self.from_version + 1:
            raise RootRotationError(
                "root transition versions must be consecutive positive versions"
            )
        if not self.old_root_key_id.strip() or not self.new_root_key_id.strip():
            raise RootRotationError("old_root_key_id and new_root_key_id are required")
        if self.old_root_key_id == self.new_root_key_id:
            raise RootRotationError("old and new root key IDs must differ")
        if self.effective_at.tzinfo is None:
            raise RootRotationError("effective_at must be timezone-aware")
        if self.transition_kind not in {"scheduled_rotation", "emergency_recovery"}:
            raise RootRotationError("unsupported root transition kind")
        if self.old_root_action not in {"retire", "revoke"}:
            raise RootRotationError("unsupported old-root action")
        if (
            self.transition_kind == "emergency_recovery"
            and self.old_root_action != "revoke"
        ):
            raise RootRotationError(
                "emergency recovery requires revocation of the old root"
            )
        for name, value in (
            ("previous_registry_fingerprint", self.previous_registry_fingerprint),
            ("new_registry_fingerprint", self.new_registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise RootRotationError(f"{name} must be a SHA-256 hex digest")
        for name, value in (
            ("old_root_signature_b64", self.old_root_signature_b64),
            ("new_root_signature_b64", self.new_root_signature_b64),
        ):
            if not value.strip():
                raise RootRotationError(f"{name} is required")
            try:
                raw = b64decode(value, validate=True)
            except Exception as exc:
                raise RootRotationError(
                    f"{name} is not valid base64"
                ) from exc
            if len(raw) != 64:
                raise RootRotationError(
                    f"{name} must contain a 64-byte Ed25519 signature"
                )

    def _payload(self) -> dict[str, object]:
        return {
            "ceremony_id": self.ceremony_id,
            "registry_id": self.registry_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "old_root_key_id": self.old_root_key_id,
            "new_root_key_id": self.new_root_key_id,
            "effective_at": self.effective_at.isoformat(),
            "transition_kind": self.transition_kind,
            "old_root_action": self.old_root_action,
            "previous_registry_fingerprint": (
                self.previous_registry_fingerprint.lower()
            ),
            "new_registry_fingerprint": self.new_registry_fingerprint.lower(),
        }

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(
            self._payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def signing_bytes(self) -> bytes:
        return json.dumps(
            self._payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @staticmethod
    def root_key_id_for(public_key: Ed25519PublicKey) -> str:
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return sha256(raw).hexdigest()

    @classmethod
    def create(
        cls,
        *,
        ceremony_id: str,
        registry_id: str,
        previous: SignedTrustedKeyRegistry,
        current: SignedTrustedKeyRegistry,
        old_root_private_key: Ed25519PrivateKey,
        new_root_private_key: Ed25519PrivateKey,
        effective_at: datetime,
        transition_kind: str,
        old_root_action: str,
    ) -> "RootRotationCeremony":
        old_root = old_root_private_key.public_key()
        new_root = new_root_private_key.public_key()
        if previous.signature is None or current.signature is None:
            raise RootRotationError("both source registries must be signed")
        if previous.signature.root_key_id != cls.root_key_id_for(old_root):
            raise RootRotationError("previous registry is not signed by the old root")
        if current.signature.root_key_id != cls.root_key_id_for(new_root):
            raise RootRotationError("new registry is not signed by the new root")

        draft = cls(
            ceremony_id=ceremony_id,
            registry_id=registry_id,
            from_version=previous.registry.version,
            to_version=current.registry.version,
            old_root_key_id=cls.root_key_id_for(old_root),
            new_root_key_id=cls.root_key_id_for(new_root),
            effective_at=effective_at,
            transition_kind=transition_kind,
            old_root_action=old_root_action,
            previous_registry_fingerprint=previous.registry.fingerprint,
            new_registry_fingerprint=current.registry.fingerprint,
            old_root_signature_b64=b64encode(b"\\x00" * 64).decode("ascii"),
            new_root_signature_b64=b64encode(b"\\x00" * 64).decode("ascii"),
        )
        payload = draft.signing_bytes()
        return cls(
            ceremony_id=draft.ceremony_id,
            registry_id=draft.registry_id,
            from_version=draft.from_version,
            to_version=draft.to_version,
            old_root_key_id=draft.old_root_key_id,
            new_root_key_id=draft.new_root_key_id,
            effective_at=draft.effective_at,
            transition_kind=draft.transition_kind,
            old_root_action=draft.old_root_action,
            previous_registry_fingerprint=draft.previous_registry_fingerprint,
            new_registry_fingerprint=draft.new_registry_fingerprint,
            old_root_signature_b64=b64encode(
                old_root_private_key.sign(payload)
            ).decode("ascii"),
            new_root_signature_b64=b64encode(
                new_root_private_key.sign(payload)
            ).decode("ascii"),
        )

    def assert_source_bindings(
        self,
        previous: SignedTrustedKeyRegistry,
        current: SignedTrustedKeyRegistry,
        old_root_public_key: Ed25519PublicKey,
        new_root_public_key: Ed25519PublicKey,
    ) -> None:
        if previous.signature is None or current.signature is None:
            raise RootRotationError("both source registries must be signed")
        old_id = self.root_key_id_for(old_root_public_key)
        new_id = self.root_key_id_for(new_root_public_key)
        if old_id != self.old_root_key_id or new_id != self.new_root_key_id:
            raise RootRotationError("root public keys do not match ceremony")
        if previous.signature.root_key_id != old_id:
            raise RootRotationError("previous registry must be signed by old root")
        if current.signature.root_key_id != new_id:
            raise RootRotationError("new registry must be signed by new root")
        if previous.registry.registry_id != self.registry_id:
            raise RootRotationError("previous registry ID does not match ceremony")
        if current.registry.registry_id != self.registry_id:
            raise RootRotationError("new registry ID does not match ceremony")
        if previous.registry.version != self.from_version:
            raise RootRotationError("previous registry version does not match ceremony")
        if current.registry.version != self.to_version:
            raise RootRotationError("new registry version does not match ceremony")
        if previous.registry.fingerprint != self.previous_registry_fingerprint:
            raise RootRotationError(
                "previous registry fingerprint does not match ceremony"
            )
        if current.registry.fingerprint != self.new_registry_fingerprint:
            raise RootRotationError(
                "new registry fingerprint does not match ceremony"
            )

        try:
            old_root_public_key.verify(
                b64decode(self.old_root_signature_b64, validate=True),
                self.signing_bytes(),
            )
            new_root_public_key.verify(
                b64decode(self.new_root_signature_b64, validate=True),
                self.signing_bytes(),
            )
        except Exception as exc:
            raise RootRotationError(
                "root rotation handoff signatures could not be verified"
            ) from exc

        if previous.signature.signed_at > self.effective_at:
            raise RootRotationError(
                "previous registry cannot be signed after root transition effective_at"
            )

    def assert_recovery_policy(self) -> None:
        if (
            self.transition_kind == "scheduled_rotation"
            and self.old_root_action != "retire"
        ):
            raise RootRotationError(
                "scheduled root rotation requires retirement of the old root"
            )
        if (
            self.transition_kind == "emergency_recovery"
            and self.old_root_action != "revoke"
        ):
            raise RootRotationError(
                "emergency recovery requires revocation of the old root"
            )
