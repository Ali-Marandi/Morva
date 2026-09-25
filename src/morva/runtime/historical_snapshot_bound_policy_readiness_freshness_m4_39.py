from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshness,
    PolicyBoundReadinessFreshnessError,
)


class HistoricalSnapshotBoundPolicyReadinessFreshnessError(ValueError):
    """Raised when policy-bound freshness cannot be tied to a historical snapshot."""


@dataclass(frozen=True, slots=True)
class HistoricalSnapshotBoundPolicyReadinessFreshness:
    binding_version: int
    snapshot_id: UUID
    snapshot_fingerprint: str
    registry_integrity_version: int
    registry_policy_count: int
    registry_fingerprint: str
    policy_bound: PolicyBoundReadinessFreshness
    fingerprint: str

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                "unsupported historical snapshot-bound freshness version"
            )
        if self.registry_integrity_version < 1:
            raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                "registry_integrity_version must be positive"
            )
        if self.registry_policy_count < 0:
            raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                "registry_policy_count cannot be negative"
            )
        for name, value in (
            ("snapshot_fingerprint", self.snapshot_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                    f"{name} must be SHA-256"
                )
        try:
            PolicyBoundReadinessFreshness(
                binding_version=self.policy_bound.binding_version,
                policy=self.policy_bound.policy,
                assessment=self.policy_bound.assessment,
            )
        except PolicyBoundReadinessFreshnessError as exc:
            raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                str(exc)
            ) from exc

        expected = _fingerprint(
            snapshot_id=self.snapshot_id,
            snapshot_fingerprint=self.snapshot_fingerprint,
            registry_integrity_version=self.registry_integrity_version,
            registry_policy_count=self.registry_policy_count,
            registry_fingerprint=self.registry_fingerprint,
            policy_fingerprint=self.policy_bound.policy.fingerprint,
            freshness_fingerprint=self.policy_bound.assessment.fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
                "historical snapshot-bound freshness fingerprint mismatch"
            )

    @property
    def fresh(self) -> bool:
        return self.policy_bound.fresh

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "snapshot": {
                "id": str(self.snapshot_id),
                "fingerprint": self.snapshot_fingerprint.lower(),
            },
            "registry": {
                "integrity_version": self.registry_integrity_version,
                "policy_count": self.registry_policy_count,
                "fingerprint": self.registry_fingerprint.lower(),
            },
            "policy_bound_freshness": self.policy_bound.to_payload(),
            "fresh": self.fresh,
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_snapshot_bound_policy_readiness_freshness(
    policy_bound: PolicyBoundReadinessFreshness,
    *,
    snapshot_id: UUID,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
) -> HistoricalSnapshotBoundPolicyReadinessFreshness:
    try:
        PolicyBoundReadinessFreshness(
            binding_version=policy_bound.binding_version,
            policy=policy_bound.policy,
            assessment=policy_bound.assessment,
        )
    except PolicyBoundReadinessFreshnessError as exc:
        raise HistoricalSnapshotBoundPolicyReadinessFreshnessError(
            str(exc)
        ) from exc

    normalized_snapshot = snapshot_fingerprint.lower()
    normalized_registry = registry_fingerprint.lower()
    fingerprint = _fingerprint(
        snapshot_id=snapshot_id,
        snapshot_fingerprint=normalized_snapshot,
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized_registry,
        policy_fingerprint=policy_bound.policy.fingerprint,
        freshness_fingerprint=policy_bound.assessment.fingerprint,
    )
    return HistoricalSnapshotBoundPolicyReadinessFreshness(
        binding_version=1,
        snapshot_id=snapshot_id,
        snapshot_fingerprint=normalized_snapshot,
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized_registry,
        policy_bound=policy_bound,
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    snapshot_id: UUID,
    snapshot_fingerprint: str,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_fingerprint: str,
    freshness_fingerprint: str,
) -> str:
    payload = {
        "binding_version": 1,
        "snapshot_id": str(snapshot_id),
        "snapshot_fingerprint": snapshot_fingerprint.lower(),
        "registry_integrity_version": registry_integrity_version,
        "registry_policy_count": registry_policy_count,
        "registry_fingerprint": registry_fingerprint.lower(),
        "policy_fingerprint": policy_fingerprint.lower(),
        "freshness_fingerprint": freshness_fingerprint.lower(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
