from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID


class HistoricalRegistryBoundFreshnessReceiptError(ValueError):
    """Raised when an M4.35 receipt cannot be bound to an M4.36 snapshot."""


@dataclass(frozen=True, slots=True)
class HistoricalRegistryBoundFreshnessReceipt:
    binding_version: int
    receipt_id: UUID
    snapshot_id: UUID
    receipt_binding_fingerprint: str
    snapshot_fingerprint: str
    registry_integrity_version: int
    registry_policy_count: int
    registry_fingerprint: str
    policy_id: str
    policy_version: int
    policy_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "unsupported historical receipt binding version"
            )
        if self.registry_integrity_version < 1:
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "registry_integrity_version must be positive"
            )
        if self.registry_policy_count < 0:
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "registry_policy_count cannot be negative"
            )
        if not self.policy_id.strip():
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "policy_id is required"
            )
        if self.policy_version < 1:
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "policy_version must be positive"
            )
        for name, value in (
            ("receipt_binding_fingerprint", self.receipt_binding_fingerprint),
            ("snapshot_fingerprint", self.snapshot_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
            ("policy_fingerprint", self.policy_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalRegistryBoundFreshnessReceiptError(
                    f"{name} must be SHA-256"
                )
        expected = _fingerprint(
            receipt_id=self.receipt_id,
            snapshot_id=self.snapshot_id,
            receipt_binding_fingerprint=self.receipt_binding_fingerprint,
            snapshot_fingerprint=self.snapshot_fingerprint,
            registry_integrity_version=self.registry_integrity_version,
            registry_policy_count=self.registry_policy_count,
            registry_fingerprint=self.registry_fingerprint,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_fingerprint=self.policy_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalRegistryBoundFreshnessReceiptError(
                "historical receipt binding fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "receipt_id": str(self.receipt_id),
            "snapshot_id": str(self.snapshot_id),
            "receipt_binding_fingerprint": self.receipt_binding_fingerprint.lower(),
            "snapshot_fingerprint": self.snapshot_fingerprint.lower(),
            "registry": {
                "integrity_version": self.registry_integrity_version,
                "policy_count": self.registry_policy_count,
                "fingerprint": self.registry_fingerprint.lower(),
            },
            "policy": {
                "policy_id": self.policy_id,
                "policy_version": self.policy_version,
                "fingerprint": self.policy_fingerprint.lower(),
            },
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_registry_bound_freshness_receipt(
    *,
    receipt_id: UUID,
    snapshot_id: UUID,
    receipt_binding_fingerprint: str,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_id: str,
    policy_version: int,
    policy_fingerprint: str,
) -> HistoricalRegistryBoundFreshnessReceipt:
    normalized_policy_id = policy_id.strip()
    normalized = {
        "receipt_binding_fingerprint": receipt_binding_fingerprint.lower(),
        "snapshot_fingerprint": snapshot_fingerprint.lower(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "policy_fingerprint": policy_fingerprint.lower(),
    }
    fingerprint = _fingerprint(
        receipt_id=receipt_id,
        snapshot_id=snapshot_id,
        receipt_binding_fingerprint=normalized["receipt_binding_fingerprint"],
        snapshot_fingerprint=normalized["snapshot_fingerprint"],
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized["registry_fingerprint"],
        policy_id=normalized_policy_id,
        policy_version=policy_version,
        policy_fingerprint=normalized["policy_fingerprint"],
    )
    return HistoricalRegistryBoundFreshnessReceipt(
        binding_version=1,
        receipt_id=receipt_id,
        snapshot_id=snapshot_id,
        receipt_binding_fingerprint=normalized["receipt_binding_fingerprint"],
        snapshot_fingerprint=normalized["snapshot_fingerprint"],
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized["registry_fingerprint"],
        policy_id=normalized_policy_id,
        policy_version=policy_version,
        policy_fingerprint=normalized["policy_fingerprint"],
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    receipt_id: UUID,
    snapshot_id: UUID,
    receipt_binding_fingerprint: str,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_id: str,
    policy_version: int,
    policy_fingerprint: str,
) -> str:
    payload = {
        "binding_version": 1,
        "receipt_id": str(receipt_id),
        "snapshot_id": str(snapshot_id),
        "receipt_binding_fingerprint": receipt_binding_fingerprint.lower(),
        "snapshot_fingerprint": snapshot_fingerprint.lower(),
        "registry_integrity_version": registry_integrity_version,
        "registry_policy_count": registry_policy_count,
        "registry_fingerprint": registry_fingerprint.lower(),
        "policy_id": policy_id,
        "policy_version": policy_version,
        "policy_fingerprint": policy_fingerprint.lower(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
