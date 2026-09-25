from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID


class FreshnessPolicyRegistrySnapshotError(ValueError):
    """Raised when a historical freshness-policy registry snapshot is invalid."""


@dataclass(frozen=True, slots=True)
class FreshnessPolicyRegistrySnapshot:
    snapshot_version: int
    integrity_version: int
    policy_count: int
    registry_fingerprint: str
    member_record_ids: tuple[UUID, ...]
    membership_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.snapshot_version != 1:
            raise FreshnessPolicyRegistrySnapshotError(
                "unsupported registry snapshot version"
            )
        if self.integrity_version < 1:
            raise FreshnessPolicyRegistrySnapshotError(
                "integrity_version must be positive"
            )
        if self.policy_count < 0:
            raise FreshnessPolicyRegistrySnapshotError(
                "policy_count cannot be negative"
            )
        if len(self.member_record_ids) != self.policy_count:
            raise FreshnessPolicyRegistrySnapshotError(
                "snapshot policy count must match member record ids"
            )
        normalized_ids = tuple(sorted(self.member_record_ids, key=lambda value: str(value)))
        if normalized_ids != self.member_record_ids:
            raise FreshnessPolicyRegistrySnapshotError(
                "member record ids must be canonically ordered"
            )
        if len(set(self.member_record_ids)) != len(self.member_record_ids):
            raise FreshnessPolicyRegistrySnapshotError(
                "member record ids must be unique"
            )
        for name, value in (
            ("registry_fingerprint", self.registry_fingerprint),
            ("membership_fingerprint", self.membership_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise FreshnessPolicyRegistrySnapshotError(
                    f"{name} must be SHA-256"
                )
        expected_membership = _membership_fingerprint(self.member_record_ids)
        if self.membership_fingerprint.lower() != expected_membership:
            raise FreshnessPolicyRegistrySnapshotError(
                "registry snapshot membership fingerprint mismatch"
            )
        expected = _snapshot_fingerprint(
            snapshot_version=self.snapshot_version,
            integrity_version=self.integrity_version,
            policy_count=self.policy_count,
            registry_fingerprint=self.registry_fingerprint,
            membership_fingerprint=self.membership_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise FreshnessPolicyRegistrySnapshotError(
                "registry snapshot fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "snapshot_version": self.snapshot_version,
            "integrity_version": self.integrity_version,
            "policy_count": self.policy_count,
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "member_record_ids": [str(value) for value in self.member_record_ids],
            "membership_fingerprint": self.membership_fingerprint.lower(),
            "fingerprint": self.fingerprint.lower(),
        }


def build_freshness_policy_registry_snapshot(
    *,
    integrity_version: int,
    policy_count: int,
    registry_fingerprint: str,
    member_record_ids: tuple[UUID, ...],
) -> FreshnessPolicyRegistrySnapshot:
    normalized_ids = tuple(sorted(member_record_ids, key=lambda value: str(value)))
    membership_fingerprint = _membership_fingerprint(normalized_ids)
    fingerprint = _snapshot_fingerprint(
        snapshot_version=1,
        integrity_version=integrity_version,
        policy_count=policy_count,
        registry_fingerprint=registry_fingerprint.lower(),
        membership_fingerprint=membership_fingerprint,
    )
    return FreshnessPolicyRegistrySnapshot(
        snapshot_version=1,
        integrity_version=integrity_version,
        policy_count=policy_count,
        registry_fingerprint=registry_fingerprint.lower(),
        member_record_ids=normalized_ids,
        membership_fingerprint=membership_fingerprint,
        fingerprint=fingerprint,
    )


def _membership_fingerprint(member_record_ids: tuple[UUID, ...]) -> str:
    payload = {
        "snapshot_version": 1,
        "member_record_ids": [str(value) for value in member_record_ids],
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _snapshot_fingerprint(
    *,
    snapshot_version: int,
    integrity_version: int,
    policy_count: int,
    registry_fingerprint: str,
    membership_fingerprint: str,
) -> str:
    payload = {
        "snapshot_version": snapshot_version,
        "integrity_version": integrity_version,
        "policy_count": policy_count,
        "registry_fingerprint": registry_fingerprint.lower(),
        "membership_fingerprint": membership_fingerprint.lower(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
