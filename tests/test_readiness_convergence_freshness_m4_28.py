from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

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
    build_scope_bound_readiness_convergence,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessError,
    assess_readiness_convergence_freshness,
)


NOW = datetime(2026, 9, 23, 18, tzinfo=timezone.utc)
SHA = "a" * 40


def _readiness() -> EvidenceReadinessAssessment:
    remediation = (
        EvidenceRemediationItem(
            role="legal_approval",
            state="blocked",
            reason_code="MISSING_BINDING",
            detail="missing legal binding",
        ),
    )
    fingerprint = _readiness_fingerprint(
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        registry_fingerprint="1" * 64,
        convergence_fingerprint="2" * 64,
        lifecycle_fingerprint=None,
        ready_roles=(),
        blocked_roles=("legal_approval",),
        remediation=remediation,
    )
    return EvidenceReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        registry_fingerprint="1" * 64,
        convergence_fingerprint="2" * 64,
        lifecycle_fingerprint=None,
        ready_roles=(),
        blocked_roles=("legal_approval",),
        remediation=remediation,
        fingerprint=fingerprint,
    )


def _verification(readiness: EvidenceReadinessAssessment):
    fingerprint = _assessment_fingerprint(
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint=readiness.fingerprint,
        binding_fingerprint="3" * 64,
        binding_verification_fingerprint="4" * 64,
        state="ready",
        blockers=(),
    )
    assessment = IntegrationExecutionReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint=readiness.fingerprint,
        binding_fingerprint="3" * 64,
        binding_verification_fingerprint="4" * 64,
        state="ready",
        blockers=(),
        fingerprint=fingerprint,
    )
    return IndependentIntegrationExecutionReadinessVerification(
        assessment=assessment,
        verified_at=NOW,
    )


def _convergence():
    readiness = _readiness()
    return build_scope_bound_readiness_convergence(
        _verification(readiness),
        readiness,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW,
    )


def test_converged_receipt_is_fresh_within_window():
    result = assess_readiness_convergence_freshness(
        _convergence(),
        observed_at=NOW + timedelta(minutes=30),
        max_age_seconds=3600,
    )

    assert result.fresh is True
    assert result.state == "fresh"
    assert result.blockers == ()


def test_receipt_becomes_stale_after_window():
    result = assess_readiness_convergence_freshness(
        _convergence(),
        observed_at=NOW + timedelta(hours=2),
        max_age_seconds=3600,
    )

    assert result.fresh is False
    assert result.state == "stale"
    assert "CONVERGENCE_STALE" in result.blockers


def test_blocked_convergence_cannot_be_fresh():
    convergence = _convergence()
    from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
        ScopeBoundReadinessConvergence,
    )

    blocked = ScopeBoundReadinessConvergence(
        convergence_version=1,
        repository=convergence.repository,
        candidate_sha=convergence.candidate_sha,
        target_environment=convergence.target_environment,
        organization_scope=convergence.organization_scope,
        organization_scope_id=convergence.organization_scope_id,
        checked_at=convergence.checked_at,
        persisted_verification_fingerprint=convergence.persisted_verification_fingerprint,
        persisted_evidence_readiness_fingerprint=convergence.persisted_evidence_readiness_fingerprint,
        current_evidence_readiness_fingerprint=convergence.current_evidence_readiness_fingerprint,
        state="blocked",
        blockers=("CURRENT_EVIDENCE_READINESS_INCOMPLETE",),
        fingerprint=_fingerprint(
            convergence_fingerprint=convergence.fingerprint,
            checked_at=convergence.checked_at,
            observed_at=NOW,
            max_age_seconds=3600,
            age_seconds=0,
            state="blocked",
            blockers=("CURRENT_EVIDENCE_READINESS_INCOMPLETE",),
        ),
    )

    with pytest.raises(ReadinessConvergenceFreshnessError):
        assess_readiness_convergence_freshness(
            blocked,
            observed_at=NOW,
            max_age_seconds=3600,
        )


def test_future_observation_is_blocked():
    result = assess_readiness_convergence_freshness(
        _convergence(),
        observed_at=NOW - timedelta(minutes=1),
        max_age_seconds=3600,
    )

    assert result.state == "stale"
    assert "CONVERGENCE_OBSERVATION_IN_FUTURE" in result.blockers


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
    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": convergence_fingerprint.lower(),
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "max_age_seconds": max_age_seconds,
        "age_seconds": age_seconds,
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
