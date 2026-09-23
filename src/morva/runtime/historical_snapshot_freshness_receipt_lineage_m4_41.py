from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID


class HistoricalSnapshotFreshnessReceiptLineageError(ValueError):
    """Raised when M4.40 cannot be linked safely to M4.37 lineage."""


@dataclass(frozen=True, slots=True)
class HistoricalSnapshotFreshnessReceiptLineage:
    lineage_version: int
    freshness_receipt_id: UUID
    historical_binding_id: UUID
    snapshot_id: UUID
    freshness_receipt_fingerprint: str
    historical_binding_fingerprint: str
    snapshot_fingerprint: str
    registry_integrity_version: int
    registry_policy_count: int
    registry_fingerprint: str
    policy_id: str
    policy_version: int
    policy_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.lineage_version != 1:
            raise HistoricalSnapshotFreshnessReceiptLineageError(
                "unsupported historical freshness receipt lineage version"
            )
        if self.registry_integrity_version < 1:
            raise HistoricalSnapshotFreshnessReceiptLineageError(
                "registry_integrity_version must be positive"
            )
        if self.registry_policy_count < 0:
            raise HistoricalSnapshotFreshnessReceiptLineageError(
                "registry_policy_count cannot be negative"
            )
        if not self.policy_id.strip():
            raise HistoricalSnapshotFreshnessReceiptLineageError("policy_id is required")
        if self.policy_version < 1:
            raise HistoricalSnapshotFreshnessReceiptLineageError(
                "policy_version must be positive"
            )
        for name, value in (
            ("freshness_receipt_fingerprint", self.freshness_receipt_fingerprint),
            ("historical_binding_fingerprint", self.historical_binding_fingerprint),
            ("snapshot_fingerprint", self.snapshot_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
            ("policy_fingerprint", self.policy_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalSnapshotFreshnessReceiptLineageError(
                    f"{name} must be SHA-256"
                )
        expected = _fingerprint(
            freshness_receipt_id=self.freshness_receipt_id,
            historical_binding_id=self.historical_binding_id,
            snapshot_id=self.snapshot_id,
            freshness_receipt_fingerprint=self.freshness_receipt_fingerprint,
            historical_binding_fingerprint=self.historical_binding_fingerprint,
            snapshot_fingerprint=self.snapshot_fingerprint,
            registry_integrity_version=self.registry_integrity_version,
            registry_policy_count=self.registry_policy_count,
            registry_fingerprint=self.registry_fingerprint,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_fingerprint=self.policy_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalSnapshotFreshnessReceiptLineageError(
                "historical freshness receipt lineage fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "lineage_version": self.lineage_version,
            "freshness_receipt_id": str(self.freshness_receipt_id),
            "historical_binding_id": str(self.historical_binding_id),
            "snapshot_id": str(self.snapshot_id),
            "freshness_receipt_fingerprint": self.freshness_receipt_fingerprint.lower(),
            "historical_binding_fingerprint": self.historical_binding_fingerprint.lower(),
            "snapshot": {
                "fingerprint": self.snapshot_fingerprint.lower(),
                "registry_integrity_version": self.registry_integrity_version,
                "registry_policy_count": self.registry_policy_count,
                "registry_fingerprint": self.registry_fingerprint.lower(),
            },
            "policy": {
                "policy_id": self.policy_id,
                "policy_version": self.policy_version,
                "fingerprint": self.policy_fingerprint.lower(),
            },
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_snapshot_freshness_receipt_lineage(
    *,
    freshness_receipt_id: UUID,
    historical_binding_id: UUID,
    snapshot_id: UUID,
    freshness_receipt_fingerprint: str,
    historical_binding_fingerprint: str,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_id: str,
    policy_version: int,
    policy_fingerprint: str,
) -> HistoricalSnapshotFreshnessReceiptLineage:
    normalized_policy_id = policy_id.strip()
    normalized = {
        "freshness_receipt_fingerprint": freshness_receipt_fingerprint.lower(),
        "historical_binding_fingerprint": historical_binding_fingerprint.lower(),
        "snapshot_fingerprint": snapshot_fingerprint.lower(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "policy_fingerprint": policy_fingerprint.lower(),
    }
    fingerprint = _fingerprint(
        freshness_receipt_id=freshness_receipt_id,
        historical_binding_id=historical_binding_id,
        snapshot_id=snapshot_id,
        freshness_receipt_fingerprint=normalized["freshness_receipt_fingerprint"],
        historical_binding_fingerprint=normalized["historical_binding_fingerprint"],
        snapshot_fingerprint=normalized["snapshot_fingerprint"],
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized["registry_fingerprint"],
        policy_id=normalized_policy_id,
        policy_version=policy_version,
        policy_fingerprint=normalized["policy_fingerprint"],
    )
    return HistoricalSnapshotFreshnessReceiptLineage(
        lineage_version=1,
        freshness_receipt_id=freshness_receipt_id,
        historical_binding_id=historical_binding_id,
        snapshot_id=snapshot_id,
        freshness_receipt_fingerprint=normalized["freshness_receipt_fingerprint"],
        historical_binding_fingerprint=normalized["historical_binding_fingerprint"],
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
    freshness_receipt_id: UUID,
    historical_binding_id: UUID,
    snapshot_id: UUID,
    freshness_receipt_fingerprint: str,
    historical_binding_fingerprint: str,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_id: str,
    policy_version: int,
    policy_fingerprint: str,
) -> str:
    payload = {
        "lineage_version": 1,
        "freshness_receipt_id": str(freshness_receipt_id),
        "historical_binding_id": str(historical_binding_id),
        "snapshot_id": str(snapshot_id),
        "freshness_receipt_fingerprint": freshness_receipt_fingerprint.lower(),
        "historical_binding_fingerprint": historical_binding_fingerprint.lower(),
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
