from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from .signed_trusted_key_registry import SignedTrustedKeyRegistry
from .trusted_key_registry import TrustedKeyRegistry


class TrustRotationError(ValueError):
    """Raised when a trusted-key registry rotation ceremony is invalid."""


@dataclass(frozen=True, slots=True)
class TrustRegistryRotationCeremony:
    ceremony_id: str
    registry_id: str
    from_version: int
    to_version: int
    old_key_id: str
    new_key_id: str
    effective_at: datetime
    previous_registry_fingerprint: str
    new_registry_fingerprint: str
    root_key_id: str

    def __post_init__(self) -> None:
        if not self.ceremony_id.strip():
            raise TrustRotationError("ceremony_id is required")
        if not self.registry_id.strip():
            raise TrustRotationError("registry_id is required")
        if self.from_version < 1 or self.to_version != self.from_version + 1:
            raise TrustRotationError(
                "rotation versions must be consecutive positive versions"
            )
        if not self.old_key_id.strip() or not self.new_key_id.strip():
            raise TrustRotationError("old_key_id and new_key_id are required")
        if self.old_key_id == self.new_key_id:
            raise TrustRotationError("old_key_id and new_key_id must differ")
        if self.effective_at.tzinfo is None:
            raise TrustRotationError("effective_at must be timezone-aware")
        for name, value in (
            ("previous_registry_fingerprint", self.previous_registry_fingerprint),
            ("new_registry_fingerprint", self.new_registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise TrustRotationError(f"{name} must be a SHA-256 hex digest")
        if not self.root_key_id.strip():
            raise TrustRotationError("root_key_id is required")

    @property
    def fingerprint(self) -> str:
        payload = {
            "ceremony_id": self.ceremony_id,
            "registry_id": self.registry_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "old_key_id": self.old_key_id,
            "new_key_id": self.new_key_id,
            "effective_at": self.effective_at.isoformat(),
            "previous_registry_fingerprint": self.previous_registry_fingerprint.lower(),
            "new_registry_fingerprint": self.new_registry_fingerprint.lower(),
            "root_key_id": self.root_key_id,
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def assert_matches(
        self,
        previous: TrustedKeyRegistry,
        current: TrustedKeyRegistry,
    ) -> None:
        if (
            previous.registry_id != self.registry_id
            or current.registry_id != self.registry_id
        ):
            raise TrustRotationError("rotation registry_id does not match source registries")
        if previous.version != self.from_version or current.version != self.to_version:
            raise TrustRotationError("rotation versions do not match source registries")
        if previous.fingerprint != self.previous_registry_fingerprint:
            raise TrustRotationError(
                "previous registry fingerprint does not match ceremony"
            )
        if current.fingerprint != self.new_registry_fingerprint:
            raise TrustRotationError(
                "new registry fingerprint does not match ceremony"
            )

        try:
            old_before = previous.key(self.old_key_id)
            old_after = current.key(self.old_key_id)
            new_after = current.key(self.new_key_id)
        except Exception as exc:
            raise TrustRotationError("rotation key records are incomplete") from exc

        try:
            previous.key(self.new_key_id)
        except Exception:
            pass
        else:
            raise TrustRotationError(
                "replacement key must not exist in the previous registry"
            )

        if old_before.status != "active":
            raise TrustRotationError("old key must be active before rotation")
        if old_after.status != "retired":
            raise TrustRotationError("old key must be retired after rotation")
        if old_after.replacement_key_id != self.new_key_id:
            raise TrustRotationError("old key must point to its replacement")
        if new_after.status != "active":
            raise TrustRotationError("replacement key must be active after rotation")
        if new_after.valid_from != self.effective_at:
            raise TrustRotationError(
                "replacement key valid_from must equal ceremony effective_at"
            )

        if len(current.keys) != len(previous.keys) + 1:
            raise TrustRotationError("rotation must add exactly one replacement key")

        previous_ids = {item.key_id for item in previous.keys}
        current_ids = {item.key_id for item in current.keys}
        if current_ids - previous_ids != {self.new_key_id}:
            raise TrustRotationError(
                "rotation must add exactly the declared replacement key"
            )

        for item in previous.keys:
            if item.key_id == self.old_key_id:
                continue
            if current.key(item.key_id) != item:
                raise TrustRotationError(
                    f"non-rotated key changed unexpectedly: {item.key_id}"
                )

    def assert_signed_registries(
        self,
        previous: SignedTrustedKeyRegistry,
        current: SignedTrustedKeyRegistry,
    ) -> None:
        if previous.signature is None or current.signature is None:
            raise TrustRotationError("both source registries must be signed")
        if previous.signature.root_key_id != self.root_key_id:
            raise TrustRotationError(
                "previous registry root key does not match ceremony"
            )
        if current.signature.root_key_id != self.root_key_id:
            raise TrustRotationError("new registry root key does not match ceremony")
        if previous.registry.registry_id != self.registry_id:
            raise TrustRotationError("previous signed registry ID does not match ceremony")
        if current.registry.registry_id != self.registry_id:
            raise TrustRotationError("new signed registry ID does not match ceremony")
        self.assert_matches(previous.registry, current.registry)
