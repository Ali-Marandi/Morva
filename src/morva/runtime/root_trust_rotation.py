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
    old_root_signature_b64: str | None
    new_root_signature_b64: str
    recovery_anchor_key_id: str | None = None
    recovery_signature_b64: str | None = None

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
        if self.transition_kind == "scheduled_rotation":
            if not self.old_root_signature_b64:
                raise RootRotationError(
                    "scheduled rotation requires the old-root signature"
                )
            if self.recovery_anchor_key_id or self.recovery_signature_b64:
                raise RootRotationError(
                    "scheduled rotation must not use recovery-anchor authorization"
                )
        else:
            if not self.recovery_anchor_key_id or not self.recovery_signature_b64:
                raise RootRotationError(
                    "emergency recovery requires recovery-anchor authorization"
                )
        for name, value in (
            ("previous_registry_fingerprint", self.previous_registry_fingerprint),
            ("new_registry_fingerprint", self.new_registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise RootRotationError(f"{name} must be a SHA-256 hex digest")
        self._validate_signature("new_root_signature_b64", self.new_root_signature_b64)
        if self.old_root_signature_b64:
            self._validate_signature(
                "old_root_signature_b64", self.old_root_signature_b64
            )
        if self.recovery_signature_b64:
            self._validate_signature(
                "recovery_signature_b64", self.recovery_signature_b64
            )

    @staticmethod
    def _validate_signature(name: str, value: str) -> None:
        try:
            raw = b64decode(value, validate=True)
        except Exception as exc:
            raise RootRotationError(f"{name} is not valid base64") from exc
        if len(raw) != 64:
            raise RootRotationError(
                f"{name} must contain a 64-byte Ed25519 signature"
            )

    @staticmethod
    def root_key_id_for(public_key: Ed25519PublicKey) -> str:
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return sha256(raw).hexdigest()

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
            "previous_registry_fingerprint": self.previous_registry_fingerprint.lower(),
            "new_registry_fingerprint": self.new_registry_fingerprint.lower(),
            "recovery_anchor_key_id": self.recovery_anchor_key_id,
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

    @classmethod
    def create(
        cls,
        *,
        ceremony_id: str,
        registry_id: str,
        previous: SignedTrustedKeyRegistry,
        current: SignedTrustedKeyRegistry,
        new_root_private_key: Ed25519PrivateKey,
        effective_at: datetime,
        transition_kind: str,
        old_root_action: str,
        old_root_private_key: Ed25519PrivateKey | None = None,
        recovery_anchor_private_key: Ed25519PrivateKey | None = None,
    ) -> "RootRotationCeremony":
        if previous.signature is None or current.signature is None:
            raise RootRotationError("both source registries must be signed")
        new_root = new_root_private_key.public_key()
        if current.signature.root_key_id != cls.root_key_id_for(new_root):
            raise RootRotationError("new registry is not signed by the new root")

        if transition_kind == "scheduled_rotation" and old_root_private_key is None:
            raise RootRotationError(
                "scheduled rotation requires the old-root private key"
            )
        if transition_kind == "emergency_recovery" and recovery_anchor_private_key is None:
            raise RootRotationError(
                "emergency recovery requires the recovery-anchor private key"
            )

        old_root_key_id = previous.signature.root_key_id
        old_root_signature = None
        if old_root_private_key is not None:
            old_root = old_root_private_key.public_key()
            if old_root_key_id != cls.root_key_id_for(old_root):
                raise RootRotationError(
                    "old-root private key does not match previous registry"
                )
            old_root_signature = "__PENDING__"

        recovery_anchor_key_id = None
        recovery_signature = None
        if recovery_anchor_private_key is not None:
            recovery_anchor_key_id = cls.root_key_id_for(
                recovery_anchor_private_key.public_key()
            )
            recovery_signature = "__PENDING__"

        draft = cls(
            ceremony_id=ceremony_id,
            registry_id=registry_id,
            from_version=previous.registry.version,
            to_version=current.registry.version,
            old_root_key_id=old_root_key_id,
            new_root_key_id=cls.root_key_id_for(new_root),
            effective_at=effective_at,
            transition_kind=transition_kind,
            old_root_action=old_root_action,
            previous_registry_fingerprint=previous.registry.fingerprint,
            new_registry_fingerprint=current.registry.fingerprint,
            old_root_signature_b64=(
                b64encode(b"\x00" * 64).decode("ascii")
                if old_root_signature
                else None
            ),
            new_root_signature_b64=b64encode(b"\x00" * 64).decode("ascii"),
            recovery_anchor_key_id=recovery_anchor_key_id,
            recovery_signature_b64=(
                b64encode(b"\x00" * 64).decode("ascii")
                if recovery_signature
                else None
            ),
        )
        payload = draft.signing_bytes()

        if transition_kind == "scheduled_rotation" and recovery_anchor_private_key:
            raise RootRotationError(
                "scheduled rotation must not use recovery-anchor authorization"
            )
        if transition_kind == "emergency_recovery" and old_root_private_key:
            old_root_signature = None

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
            old_root_signature_b64=(
                b64encode(old_root_private_key.sign(payload)).decode("ascii")
                if old_root_private_key is not None
                and transition_kind == "scheduled_rotation"
                else None
            ),
            new_root_signature_b64=b64encode(
                new_root_private_key.sign(payload)
            ).decode("ascii"),
            recovery_anchor_key_id=draft.recovery_anchor_key_id,
            recovery_signature_b64=(
                b64encode(recovery_anchor_private_key.sign(payload)).decode("ascii")
                if recovery_anchor_private_key is not None
                and transition_kind == "emergency_recovery"
                else None
            ),
        )

    def assert_source_bindings(
        self,
        previous: SignedTrustedKeyRegistry,
        current: SignedTrustedKeyRegistry,
        old_root_public_key: Ed25519PublicKey,
        new_root_public_key: Ed25519PublicKey,
        recovery_anchor_public_key: Ed25519PublicKey | None = None,
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
        if previous.signature.signed_at > self.effective_at:
            raise RootRotationError(
                "previous registry cannot be signed after root transition effective_at"
            )

        try:
            new_root_public_key.verify(
                b64decode(self.new_root_signature_b64, validate=True),
                self.signing_bytes(),
            )
            if self.transition_kind == "scheduled_rotation":
                old_root_public_key.verify(
                    b64decode(self.old_root_signature_b64 or "", validate=True),
                    self.signing_bytes(),
                )
            else:
                if recovery_anchor_public_key is None:
                    raise RootRotationError(
                        "emergency recovery requires recovery-anchor public key"
                    )
                recovery_id = self.root_key_id_for(recovery_anchor_public_key)
                if recovery_id != self.recovery_anchor_key_id:
                    raise RootRotationError(
                        "recovery-anchor public key does not match ceremony"
                    )
                recovery_anchor_public_key.verify(
                    b64decode(self.recovery_signature_b64 or "", validate=True),
                    self.signing_bytes(),
                )
        except RootRotationError:
            raise
        except Exception as exc:
            raise RootRotationError(
                "root transition authorization signatures could not be verified"
            ) from exc
