from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


class ReadinessConvergenceFreshnessPolicyError(ValueError):
    """Raised when a readiness convergence freshness policy is invalid."""


@dataclass(frozen=True, slots=True)
class ReadinessConvergenceFreshnessPolicy:
    policy_version: int
    policy_id: str
    max_age_seconds: int
    fingerprint: str

    def __post_init__(self) -> None:
        if self.policy_version < 1:
            raise ReadinessConvergenceFreshnessPolicyError(
                "policy_version must be positive"
            )
        policy_id = self.policy_id.strip()
        if not policy_id:
            raise ReadinessConvergenceFreshnessPolicyError(
                "policy_id is required"
            )
        if len(policy_id) > 100:
            raise ReadinessConvergenceFreshnessPolicyError(
                "policy_id must not exceed 100 characters"
            )
        if self.max_age_seconds < 1:
            raise ReadinessConvergenceFreshnessPolicyError(
                "max_age_seconds must be positive"
            )
        if len(self.fingerprint) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.fingerprint.lower()
        ):
            raise ReadinessConvergenceFreshnessPolicyError(
                "fingerprint must be SHA-256"
            )
        expected = _fingerprint(
            policy_version=self.policy_version,
            policy_id=policy_id,
            max_age_seconds=self.max_age_seconds,
        )
        if self.fingerprint.lower() != expected:
            raise ReadinessConvergenceFreshnessPolicyError(
                "freshness policy fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "policy_id": self.policy_id,
            "max_age_seconds": self.max_age_seconds,
            "fingerprint": self.fingerprint.lower(),
        }


def build_freshness_policy(
    *,
    policy_id: str,
    max_age_seconds: int,
    policy_version: int = 1,
) -> ReadinessConvergenceFreshnessPolicy:
    policy_id = policy_id.strip()
    if policy_version < 1:
        raise ReadinessConvergenceFreshnessPolicyError(
            "policy_version must be positive"
        )
    fingerprint = _fingerprint(
        policy_version=policy_version,
        policy_id=policy_id,
        max_age_seconds=max_age_seconds,
    )
    return ReadinessConvergenceFreshnessPolicy(
        policy_version=policy_version,
        policy_id=policy_id,
        max_age_seconds=max_age_seconds,
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    policy_version: int,
    policy_id: str,
    max_age_seconds: int,
) -> str:
    payload = {
        "policy_version": policy_version,
        "policy_id": policy_id,
        "max_age_seconds": max_age_seconds,
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
