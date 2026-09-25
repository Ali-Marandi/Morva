from __future__ import annotations

from dataclasses import dataclass

from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
    ReadinessConvergenceFreshnessError,
    assess_readiness_convergence_freshness,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicy,
    ReadinessConvergenceFreshnessPolicyError,
)


class PolicyBoundReadinessFreshnessError(ValueError):
    """Raised when a freshness result cannot be bound to its policy."""


@dataclass(frozen=True, slots=True)
class PolicyBoundReadinessFreshness:
    binding_version: int
    policy: ReadinessConvergenceFreshnessPolicy
    assessment: ReadinessConvergenceFreshnessAssessment

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise PolicyBoundReadinessFreshnessError(
                "unsupported policy-bound freshness version"
            )
        if self.assessment.max_age_seconds != self.policy.max_age_seconds:
            raise PolicyBoundReadinessFreshnessPolicyMismatch(
                "freshness assessment max age does not match policy"
            )

    @property
    def fresh(self) -> bool:
        return self.assessment.fresh

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "policy": self.policy.to_payload(),
            "freshness": self.assessment.to_payload(),
        }


class PolicyBoundReadinessFreshnessPolicyMismatch(
    PolicyBoundReadinessFreshnessError
):
    """Raised when a freshness assessment was produced under another policy."""


def build_policy_bound_freshness(
    policy: ReadinessConvergenceFreshnessPolicy,
    convergence,
    *,
    observed_at,
) -> PolicyBoundReadinessFreshness:
    try:
        assessment = assess_readiness_convergence_freshness(
            convergence,
            observed_at=observed_at,
            max_age_seconds=policy.max_age_seconds,
        )
    except ReadinessConvergenceFreshnessError as exc:
        raise PolicyBoundReadinessFreshnessError(str(exc)) from exc
    return PolicyBoundReadinessFreshness(
        binding_version=1,
        policy=policy,
        assessment=assessment,
    )


def validate_policy(policy: ReadinessConvergenceFreshnessPolicy) -> None:
    try:
        ReadinessConvergenceFreshnessPolicy(
            policy_version=policy.policy_version,
            policy_id=policy.policy_id,
            max_age_seconds=policy.max_age_seconds,
            fingerprint=policy.fingerprint,
        )
    except ReadinessConvergenceFreshnessPolicyError as exc:
        raise PolicyBoundReadinessFreshnessError(str(exc)) from exc
