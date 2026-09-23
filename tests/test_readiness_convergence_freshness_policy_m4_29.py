from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicyError,
    build_freshness_policy,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshness,
    PolicyBoundReadinessFreshnessError,
    build_policy_bound_freshness,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
)


NOW = datetime(2026, 9, 23, 18, tzinfo=timezone.utc)


def _assessment(max_age_seconds: int) -> ReadinessConvergenceFreshnessAssessment:
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=max_age_seconds,
    )
    fingerprint = _fingerprint(
        convergence_fingerprint="a" * 64,
        checked_at=NOW,
        observed_at=NOW,
        max_age_seconds=max_age_seconds,
        age_seconds=0,
        state="fresh",
        blockers=(),
    )
    return ReadinessConvergenceFreshnessAssessment(
        freshness_version=1,
        convergence_fingerprint="a" * 64,
        checked_at=NOW,
        observed_at=NOW,
        max_age_seconds=policy.max_age_seconds,
        age_seconds=0,
        state="fresh",
        blockers=(),
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    convergence_fingerprint: str,
    checked_at: datetime,
    observed_at: datetime,
    max_age_seconds: int,
    age_seconds: int,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    import hashlib
    import json

    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": convergence_fingerprint,
        "checked_at": checked_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "max_age_seconds": max_age_seconds,
        "age_seconds": age_seconds,
        "state": state,
        "blockers": list(blockers),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def test_policy_fingerprint_is_deterministic():
    first = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )
    second = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )

    assert first.fingerprint == second.fingerprint


def test_policy_rejects_tampered_fingerprint():
    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyError,
        match="fingerprint mismatch",
    ):
        from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
            ReadinessConvergenceFreshnessPolicy,
        )

        ReadinessConvergenceFreshnessPolicy(
            policy_version=1,
            policy_id="integration-staging-v1",
            max_age_seconds=3600,
            fingerprint="f" * 64,
        )


def test_policy_bound_assessment_requires_matching_policy():
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )
    bound = build_policy_bound_freshness(
        policy,
        _convergence(),
        observed_at=NOW,
    )

    assert isinstance(bound, PolicyBoundReadinessFreshness)
    assert bound.policy.fingerprint == policy.fingerprint
    assert bound.assessment.max_age_seconds == 3600


def test_policy_bound_assessment_rejects_mismatched_policy():
    assessment = _assessment(3600)
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=7200,
    )

    with pytest.raises(PolicyBoundReadinessFreshnessError):
        PolicyBoundReadinessFreshness(
            binding_version=1,
            policy=policy,
            assessment=assessment,
        )


def _convergence():
    from morva.runtime.evidence_closure_matrix import CLOSURE_ROLE_SOURCE_TYPES
    from morva.runtime.evidence_readiness import (
        EvidenceReadinessAssessment,
        _readiness_fingerprint,
    )
    from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
        IndependentIntegrationExecutionReadinessVerification,
    )
    from morva.runtime.integration_execution_readiness_assessment import (
        IntegrationExecutionReadinessAssessment,
        _assessment_fingerprint,
    )
    from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
        build_scope_bound_readiness_convergence,
    )

    readiness_fingerprint = _readiness_fingerprint(
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        registry_fingerprint="1" * 64,
        convergence_fingerprint="2" * 64,
        lifecycle_fingerprint=None,
        ready_roles=tuple(CLOSURE_ROLE_SOURCE_TYPES),
        blocked_roles=(),
        remediation=(),
    )
    readiness = EvidenceReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        registry_fingerprint="1" * 64,
        convergence_fingerprint="2" * 64,
        lifecycle_fingerprint=None,
        ready_roles=tuple(CLOSURE_ROLE_SOURCE_TYPES),
        blocked_roles=(),
        remediation=(),
        fingerprint=readiness_fingerprint,
    )
    assessment_fingerprint = _assessment_fingerprint(
        repository="Ali-Marandi/Morva",
        candidate_sha="d" * 40,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint=readiness.fingerprint,
        binding_fingerprint="3" * 64,
        binding_verification_fingerprint="4" * 64,
        state="ready",
        blockers=(),
    )
    verification = IndependentIntegrationExecutionReadinessVerification(
        assessment=IntegrationExecutionReadinessAssessment(
            assessment_version=1,
            repository="Ali-Marandi/Morva",
            candidate_sha="d" * 40,
            target_environment="staging",
            checked_at=NOW,
            evidence_readiness_fingerprint=readiness.fingerprint,
            binding_fingerprint="3" * 64,
            binding_verification_fingerprint="4" * 64,
            state="ready",
            blockers=(),
            fingerprint=assessment_fingerprint,
        ),
        verified_at=NOW,
    )
    return build_scope_bound_readiness_convergence(
        verification,
        readiness,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW,
    )
