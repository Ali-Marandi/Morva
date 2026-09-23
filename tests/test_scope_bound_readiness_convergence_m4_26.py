from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from morva.runtime.evidence_readiness import (
    EvidenceReadinessAssessment,
    EvidenceRemediationItem,
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
    ScopeBoundReadinessConvergenceError,
    build_scope_bound_readiness_convergence,
)


NOW = datetime(2026, 9, 23, 15, tzinfo=timezone.utc)
SHA = "e" * 40


def _evidence_readiness(*, complete: bool, checked_at: datetime) -> EvidenceReadinessAssessment:
    ready_roles = ("legal_approval",) if complete else ()
    blocked_roles = () if complete else ("finance_approval",)
    remediation = () if complete else (
        EvidenceRemediationItem(
            role="finance_approval",
            state="blocked",
            reason_code="MISSING_BINDING",
            detail="Create a current finance binding.",
        ),
    )
    fingerprint = _readiness_fingerprint(
        repository="Ali-Marandi/Morva",
        checked_at=checked_at,
        registry_fingerprint="3" * 64,
        convergence_fingerprint="4" * 64,
        lifecycle_fingerprint=None,
        ready_roles=ready_roles,
        blocked_roles=blocked_roles,
        remediation=remediation,
    )
    return EvidenceReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        checked_at=checked_at,
        registry_fingerprint="3" * 64,
        convergence_fingerprint="4" * 64,
        lifecycle_fingerprint=None,
        ready_roles=ready_roles,
        blocked_roles=blocked_roles,
        remediation=remediation,
        fingerprint=fingerprint,
    )


def _verification(evidence_readiness: EvidenceReadinessAssessment):
    assessment_fingerprint = _assessment_fingerprint(
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint=evidence_readiness.fingerprint,
        binding_fingerprint="5" * 64,
        binding_verification_fingerprint="6" * 64,
        state="ready",
        blockers=(),
    )
    readiness = IntegrationExecutionReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint=evidence_readiness.fingerprint,
        binding_fingerprint="5" * 64,
        binding_verification_fingerprint="6" * 64,
        state="ready",
        blockers=(),
        fingerprint=assessment_fingerprint,
    )
    return IndependentIntegrationExecutionReadinessVerification(
        assessment=readiness,
        verified_at=NOW + timedelta(minutes=1),
    )


def test_scope_bound_readiness_converges_when_scoped_evidence_fingerprint_matches():
    current = _evidence_readiness(complete=True, checked_at=NOW)
    verification = _verification(current)

    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=2),
    )

    assert result.converged is True
    assert result.state == "converged"
    assert result.blockers == ()


def test_scope_bound_readiness_ignores_observation_time_only():
    persisted = _evidence_readiness(complete=True, checked_at=NOW)
    current = _evidence_readiness(
        complete=True,
        checked_at=NOW + timedelta(minutes=5),
    )
    verification = _verification(persisted)

    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=6),
    )

    assert result.converged is True
    assert result.blockers == ()


def test_scope_bound_readiness_blocks_when_current_evidence_changes():
    persisted = _evidence_readiness(complete=True, checked_at=NOW)
    current = _evidence_readiness(
        complete=False,
        checked_at=NOW + timedelta(minutes=5),
    )
    verification = _verification(persisted)

    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=6),
    )

    assert result.converged is False
    assert "CURRENT_EVIDENCE_READINESS_INCOMPLETE" in result.blockers
    assert "EVIDENCE_READINESS_FINGERPRINT_MISMATCH" in result.blockers


def test_scope_bound_readiness_blocks_incomplete_current_evidence():
    persisted = _evidence_readiness(complete=True, checked_at=NOW)
    current = _evidence_readiness(
        complete=False,
        checked_at=NOW + timedelta(minutes=5),
    )
    verification = _verification(persisted)

    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=6),
    )

    assert result.converged is False
    assert "CURRENT_EVIDENCE_READINESS_INCOMPLETE" in result.blockers


def test_convergence_fingerprint_tamper_is_rejected():
    current = _evidence_readiness(complete=True, checked_at=NOW)
    verification = _verification(current)
    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=2),
    )

    with pytest.raises(
        ScopeBoundReadinessConvergenceError,
        match="fingerprint mismatch",
    ):
        type(result)(
            convergence_version=result.convergence_version,
            repository=result.repository,
            candidate_sha=result.candidate_sha,
            target_environment=result.target_environment,
            organization_scope=result.organization_scope,
            organization_scope_id=result.organization_scope_id,
            checked_at=result.checked_at,
            persisted_verification_fingerprint=result.persisted_verification_fingerprint,
            persisted_evidence_readiness_fingerprint=
                result.persisted_evidence_readiness_fingerprint,
            current_evidence_readiness_fingerprint=result.current_evidence_readiness_fingerprint,
            state=result.state,
            blockers=result.blockers,
            fingerprint="f" * 64,
        )


def test_future_verified_at_is_blocked():
    current = _evidence_readiness(complete=True, checked_at=NOW)
    verification = IndependentIntegrationExecutionReadinessVerification(
        assessment=_verification(current).assessment,
        verified_at=NOW + timedelta(minutes=10),
    )

    result = build_scope_bound_readiness_convergence(
        verification,
        current,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW + timedelta(minutes=5),
    )

    assert result.converged is False
    assert "VERIFICATION_TIME_IN_FUTURE" in result.blockers
