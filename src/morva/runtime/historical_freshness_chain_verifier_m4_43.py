from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.runtime.historical_registry_bound_freshness_receipt_m4_37 import (
    HistoricalRegistryBoundFreshnessReceipt,
)
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    HistoricalSnapshotBoundPolicyReadinessFreshness,
)
from morva.runtime.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineage,
)
from morva.runtime.readiness_freshness_policy_registry_snapshot_m4_36 import (
    FreshnessPolicyRegistrySnapshot,
)


class HistoricalFreshnessChainVerificationError(ValueError):
    """Raised when M4.43 inputs cannot form a valid verification result."""


@dataclass(frozen=True, slots=True)
class HistoricalFreshnessChainVerification:
    verification_version: int
    freshness_receipt_id: UUID
    historical_binding_id: UUID
    snapshot_id: UUID
    lineage_fingerprint: str
    freshness_receipt_fingerprint: str
    historical_binding_fingerprint: str
    snapshot_fingerprint: str
    policy_id: str
    policy_version: int
    policy_fingerprint: str
    registry_integrity_version: int
    registry_policy_count: int
    registry_fingerprint: str
    state: str
    blockers: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.verification_version != 1:
            raise HistoricalFreshnessChainVerificationError(
                "unsupported historical freshness chain verification version"
            )
        if self.state not in {"verified", "blocked"}:
            raise HistoricalFreshnessChainVerificationError(
                "state must be verified or blocked"
            )
        if self.state == "verified" and self.blockers:
            raise HistoricalFreshnessChainVerificationError(
                "verified chain cannot contain blockers"
            )
        if self.state == "blocked" and not self.blockers:
            raise HistoricalFreshnessChainVerificationError(
                "blocked chain must contain at least one blocker"
            )
        for name, value in (
            ("lineage_fingerprint", self.lineage_fingerprint),
            ("freshness_receipt_fingerprint", self.freshness_receipt_fingerprint),
            ("historical_binding_fingerprint", self.historical_binding_fingerprint),
            ("snapshot_fingerprint", self.snapshot_fingerprint),
            ("policy_fingerprint", self.policy_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalFreshnessChainVerificationError(
                    f"{name} must be SHA-256"
                )
        if not self.policy_id.strip():
            raise HistoricalFreshnessChainVerificationError("policy_id is required")
        if self.policy_version < 1:
            raise HistoricalFreshnessChainVerificationError(
                "policy_version must be positive"
            )
        if self.registry_integrity_version < 1:
            raise HistoricalFreshnessChainVerificationError(
                "registry_integrity_version must be positive"
            )
        if self.registry_policy_count < 0:
            raise HistoricalFreshnessChainVerificationError(
                "registry_policy_count cannot be negative"
            )
        expected = _fingerprint(
            freshness_receipt_id=self.freshness_receipt_id,
            historical_binding_id=self.historical_binding_id,
            snapshot_id=self.snapshot_id,
            lineage_fingerprint=self.lineage_fingerprint,
            freshness_receipt_fingerprint=self.freshness_receipt_fingerprint,
            historical_binding_fingerprint=self.historical_binding_fingerprint,
            snapshot_fingerprint=self.snapshot_fingerprint,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            policy_fingerprint=self.policy_fingerprint,
            registry_integrity_version=self.registry_integrity_version,
            registry_policy_count=self.registry_policy_count,
            registry_fingerprint=self.registry_fingerprint,
            state=self.state,
            blockers=self.blockers,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalFreshnessChainVerificationError(
                "historical freshness chain verification fingerprint mismatch"
            )

    @property
    def valid(self) -> bool:
        return self.state == "verified"

    def to_payload(self) -> dict[str, object]:
        return {
            "verification_version": self.verification_version,
            "freshness_receipt_id": str(self.freshness_receipt_id),
            "historical_binding_id": str(self.historical_binding_id),
            "snapshot_id": str(self.snapshot_id),
            "lineage_fingerprint": self.lineage_fingerprint.lower(),
            "freshness_receipt_fingerprint": self.freshness_receipt_fingerprint.lower(),
            "historical_binding_fingerprint": self.historical_binding_fingerprint.lower(),
            "snapshot_fingerprint": self.snapshot_fingerprint.lower(),
            "policy": {
                "policy_id": self.policy_id,
                "policy_version": self.policy_version,
                "fingerprint": self.policy_fingerprint.lower(),
            },
            "registry": {
                "integrity_version": self.registry_integrity_version,
                "policy_count": self.registry_policy_count,
                "fingerprint": self.registry_fingerprint.lower(),
            },
            "state": self.state,
            "blockers": list(self.blockers),
            "valid": self.valid,
            "fingerprint": self.fingerprint.lower(),
        }


def verify_historical_freshness_chain(
    *,
    freshness_receipt_id: UUID,
    freshness: HistoricalSnapshotBoundPolicyReadinessFreshness,
    historical_binding_id: UUID,
    historical_binding: HistoricalRegistryBoundFreshnessReceipt,
    snapshot_id: UUID,
    snapshot: FreshnessPolicyRegistrySnapshot,
    lineage: HistoricalSnapshotFreshnessReceiptLineage,
) -> HistoricalFreshnessChainVerification:
    blockers: list[str] = []

    policy = freshness.policy_bound.policy

    pairs = (
        (
            "FRESHNESS_RECEIPT_ID_MISMATCH",
            freshness_receipt_id,
            lineage.freshness_receipt_id,
        ),
        (
            "HISTORICAL_BINDING_ID_MISMATCH",
            historical_binding_id,
            lineage.historical_binding_id,
        ),
        ("SNAPSHOT_ID_MISMATCH", snapshot_id, lineage.snapshot_id),
        ("FRESHNESS_SNAPSHOT_ID_MISMATCH", freshness.snapshot_id, snapshot_id),
        ("BINDING_SNAPSHOT_ID_MISMATCH", historical_binding.snapshot_id, snapshot_id),
        (
            "LINEAGE_RECEIPT_FINGERPRINT_MISMATCH",
            lineage.freshness_receipt_fingerprint,
            freshness.fingerprint,
        ),
        (
            "LINEAGE_BINDING_FINGERPRINT_MISMATCH",
            lineage.historical_binding_fingerprint,
            historical_binding.fingerprint,
        ),
        (
            "LINEAGE_SNAPSHOT_FINGERPRINT_MISMATCH",
            lineage.snapshot_fingerprint,
            snapshot.fingerprint,
        ),
        (
            "FRESHNESS_SNAPSHOT_FINGERPRINT_MISMATCH",
            freshness.snapshot_fingerprint,
            snapshot.fingerprint,
        ),
        (
            "BINDING_SNAPSHOT_FINGERPRINT_MISMATCH",
            historical_binding.snapshot_fingerprint,
            snapshot.fingerprint,
        ),
        ("LINEAGE_POLICY_ID_MISMATCH", lineage.policy_id, policy.policy_id),
        ("BINDING_POLICY_ID_MISMATCH", historical_binding.policy_id, policy.policy_id),
        ("LINEAGE_POLICY_VERSION_MISMATCH", lineage.policy_version, policy.policy_version),
        (
            "BINDING_POLICY_VERSION_MISMATCH",
            historical_binding.policy_version,
            policy.policy_version,
        ),
        ("LINEAGE_POLICY_FINGERPRINT_MISMATCH", lineage.policy_fingerprint, policy.fingerprint),
        (
            "BINDING_POLICY_FINGERPRINT_MISMATCH",
            historical_binding.policy_fingerprint,
            policy.fingerprint,
        ),
        (
            "LINEAGE_REGISTRY_VERSION_MISMATCH",
            lineage.registry_integrity_version,
            snapshot.integrity_version,
        ),
        (
            "FRESHNESS_REGISTRY_VERSION_MISMATCH",
            freshness.registry_integrity_version,
            snapshot.integrity_version,
        ),
        (
            "BINDING_REGISTRY_VERSION_MISMATCH",
            historical_binding.registry_integrity_version,
            snapshot.integrity_version,
        ),
        ("LINEAGE_REGISTRY_COUNT_MISMATCH", lineage.registry_policy_count, snapshot.policy_count),
        (
            "FRESHNESS_REGISTRY_COUNT_MISMATCH",
            freshness.registry_policy_count,
            snapshot.policy_count,
        ),
        (
            "BINDING_REGISTRY_COUNT_MISMATCH",
            historical_binding.registry_policy_count,
            snapshot.policy_count,
        ),
        (
            "LINEAGE_REGISTRY_FINGERPRINT_MISMATCH",
            lineage.registry_fingerprint,
            snapshot.registry_fingerprint,
        ),
        (
            "FRESHNESS_REGISTRY_FINGERPRINT_MISMATCH",
            freshness.registry_fingerprint,
            snapshot.registry_fingerprint,
        ),
        (
            "BINDING_REGISTRY_FINGERPRINT_MISMATCH",
            historical_binding.registry_fingerprint,
            snapshot.registry_fingerprint,
        ),
    )
    for blocker, left, right in pairs:
        if left != right:
            blockers.append(blocker)

    # The M4.37 binding must point to the exact M4.35 receipt that was the
    # source of the historical binding; this is structurally separate from
    # the M4.40 historical freshness receipt ID.
    if historical_binding.snapshot_id != lineage.snapshot_id:
        blockers.append("HISTORICAL_BINDING_LINEAGE_SNAPSHOT_MISMATCH")

    normalized_blockers = tuple(dict.fromkeys(blockers))
    state = "verified" if not normalized_blockers else "blocked"
    fingerprint = _fingerprint(
        freshness_receipt_id=freshness_receipt_id,
        historical_binding_id=historical_binding_id,
        snapshot_id=snapshot_id,
        lineage_fingerprint=lineage.fingerprint,
        freshness_receipt_fingerprint=freshness.fingerprint,
        historical_binding_fingerprint=historical_binding.fingerprint,
        snapshot_fingerprint=snapshot.fingerprint,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_fingerprint=policy.fingerprint,
        registry_integrity_version=snapshot.integrity_version,
        registry_policy_count=snapshot.policy_count,
        registry_fingerprint=snapshot.registry_fingerprint,
        state=state,
        blockers=normalized_blockers,
    )
    return HistoricalFreshnessChainVerification(
        verification_version=1,
        freshness_receipt_id=freshness_receipt_id,
        historical_binding_id=historical_binding_id,
        snapshot_id=snapshot_id,
        lineage_fingerprint=lineage.fingerprint.lower(),
        freshness_receipt_fingerprint=freshness.fingerprint.lower(),
        historical_binding_fingerprint=historical_binding.fingerprint.lower(),
        snapshot_fingerprint=snapshot.fingerprint.lower(),
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_fingerprint=policy.fingerprint.lower(),
        registry_integrity_version=snapshot.integrity_version,
        registry_policy_count=snapshot.policy_count,
        registry_fingerprint=snapshot.registry_fingerprint.lower(),
        state=state,
        blockers=normalized_blockers,
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    freshness_receipt_id: UUID,
    historical_binding_id: UUID,
    snapshot_id: UUID,
    lineage_fingerprint: str,
    freshness_receipt_fingerprint: str,
    historical_binding_fingerprint: str,
    snapshot_fingerprint: str,
    policy_id: str,
    policy_version: int,
    policy_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "freshness_receipt_id": str(freshness_receipt_id),
        "historical_binding_id": str(historical_binding_id),
        "snapshot_id": str(snapshot_id),
        "lineage_fingerprint": lineage_fingerprint.lower(),
        "freshness_receipt_fingerprint": freshness_receipt_fingerprint.lower(),
        "historical_binding_fingerprint": historical_binding_fingerprint.lower(),
        "snapshot_fingerprint": snapshot_fingerprint.lower(),
        "policy_id": policy_id,
        "policy_version": policy_version,
        "policy_fingerprint": policy_fingerprint.lower(),
        "registry_integrity_version": registry_integrity_version,
        "registry_policy_count": registry_policy_count,
        "registry_fingerprint": registry_fingerprint.lower(),
        "state": state,
        "blockers": list(blockers),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()