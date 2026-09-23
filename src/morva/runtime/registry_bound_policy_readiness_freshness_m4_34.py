from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshness,
    PolicyBoundReadinessFreshnessError,
)


class RegistryBoundPolicyReadinessFreshnessError(ValueError):
    """Raised when a policy-bound freshness result cannot be bound to a registry snapshot."""


@dataclass(frozen=True, slots=True)
class RegistryBoundPolicyReadinessFreshness:
    binding_version: int
    registry_integrity_version: int
    registry_policy_count: int
    registry_fingerprint: str
    policy_bound: PolicyBoundReadinessFreshness
    fingerprint: str

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise RegistryBoundPolicyReadinessFreshnessError(
                "unsupported registry-bound freshness version"
            )
        if self.registry_integrity_version < 1:
            raise RegistryBoundPolicyReadinessFreshnessError(
                "registry_integrity_version must be positive"
            )
        if self.registry_policy_count < 0:
            raise RegistryBoundPolicyReadinessFreshnessError(
                "registry_policy_count cannot be negative"
            )
        if len(self.registry_fingerprint) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.registry_fingerprint.lower()
        ):
            raise RegistryBoundPolicyReadinessFreshnessError(
                "registry_fingerprint must be SHA-256"
            )
        try:
            PolicyBoundReadinessFreshness(
                binding_version=self.policy_bound.binding_version,
                policy=self.policy_bound.policy,
                assessment=self.policy_bound.assessment,
            )
        except PolicyBoundReadinessFreshnessError as exc:
            raise RegistryBoundPolicyReadinessFreshnessError(
                str(exc)
            ) from exc

        expected = _fingerprint(
            registry_integrity_version=self.registry_integrity_version,
            registry_policy_count=self.registry_policy_count,
            registry_fingerprint=self.registry_fingerprint,
            policy_fingerprint=self.policy_bound.policy.fingerprint,
            freshness_fingerprint=self.policy_bound.assessment.fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise RegistryBoundPolicyReadinessFreshnessError(
                "registry-bound freshness fingerprint mismatch"
            )

    @property
    def fresh(self) -> bool:
        return self.policy_bound.fresh

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "registry": {
                "integrity_version": self.registry_integrity_version,
                "policy_count": self.registry_policy_count,
                "fingerprint": self.registry_fingerprint.lower(),
            },
            "policy_bound_freshness": self.policy_bound.to_payload(),
            "fresh": self.fresh,
            "fingerprint": self.fingerprint,
        }


def build_registry_bound_policy_readiness_freshness(
    policy_bound: PolicyBoundReadinessFreshness,
    *,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
) -> RegistryBoundPolicyReadinessFreshness:
    try:
        PolicyBoundReadinessFreshness(
            binding_version=policy_bound.binding_version,
            policy=policy_bound.policy,
            assessment=policy_bound.assessment,
        )
    except PolicyBoundReadinessFreshnessError as exc:
        raise RegistryBoundPolicyReadinessFreshnessError(str(exc)) from exc

    normalized = registry_fingerprint.lower()
    fingerprint = _fingerprint(
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized,
        policy_fingerprint=policy_bound.policy.fingerprint,
        freshness_fingerprint=policy_bound.assessment.fingerprint,
    )
    return RegistryBoundPolicyReadinessFreshness(
        binding_version=1,
        registry_integrity_version=registry_integrity_version,
        registry_policy_count=registry_policy_count,
        registry_fingerprint=normalized,
        policy_bound=policy_bound,
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    registry_integrity_version: int,
    registry_policy_count: int,
    registry_fingerprint: str,
    policy_fingerprint: str,
    freshness_fingerprint: str,
) -> str:
    payload = {
        "binding_version": 1,
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
