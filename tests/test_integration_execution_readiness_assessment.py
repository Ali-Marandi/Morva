from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

import pytest

from morva.runtime.integration_execution_evidence_binding_verifier import (
    IntegrationExecutionEvidenceBindingVerification,
)
from morva.runtime.integration_execution_evidence_bridge import (
    IntegrationExecutionEvidenceBinding,
)
from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessmentError,
    build_integration_execution_readiness_assessment,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
SHA = "b" * 40
FP = "a" * 64


@dataclass(frozen=True)
class FakeEvidenceReadiness:
    complete: bool
    registry_fingerprint: str
    fingerprint: str


def _binding(registry_fingerprint: str = FP) -> IntegrationExecutionEvidenceBinding:
    return IntegrationExecutionEvidenceBinding(
        binding_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment="staging",
        execution_id="EXEC-001",
        execution_evidence_fingerprint="1" * 64,
        execution_verification_fingerprint="2" * 64,
        execution_readiness_fingerprint="3" * 64,
        registry_fingerprint=registry_fingerprint,
        adapter_evidence_bindings=(
            ("sina", "E-SINA", "4" * 64),
            ("accounting", "E-ACCOUNTING", "5" * 64),
            ("treasury", "E-TREASURY", "6" * 64),
            ("bank", "E-BANK", "7" * 64),
            ("tax", "E-TAX", "8" * 64),
            ("insurance", "E-INSURANCE", "9" * 64),
        ),
        bound_by="operator",
        bound_at=NOW,
    )


def _verification(registry_fingerprint: str = FP) -> IntegrationExecutionEvidenceBindingVerification:
    return IntegrationExecutionEvidenceBindingVerification(
        binding=_binding(registry_fingerprint),
        verified_at=NOW,
    )


def test_ready_when_execution_binding_is_verified_and_evidence_is_complete():
    readiness = FakeEvidenceReadiness(
        complete=True,
        registry_fingerprint=FP,
        fingerprint="c" * 64,
    )

    assessment = build_integration_execution_readiness_assessment(
        readiness,
        _verification(),
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        checked_at=NOW,
    )

    assert assessment.ready
    assert assessment.state == "ready"
    assert assessment.blockers == ()
    assert len(assessment.fingerprint) == 64


def test_incomplete_authoritative_evidence_blocks_readiness():
    readiness = FakeEvidenceReadiness(
        complete=False,
        registry_fingerprint=FP,
        fingerprint="c" * 64,
    )

    assessment = build_integration_execution_readiness_assessment(
        readiness,
        _verification(),
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        checked_at=NOW,
    )

    assert assessment.state == "blocked"
    assert assessment.blockers == ("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE",)


def test_registry_mismatch_blocks_readiness():
    readiness = FakeEvidenceReadiness(
        complete=True,
        registry_fingerprint="d" * 64,
        fingerprint="c" * 64,
    )

    assessment = build_integration_execution_readiness_assessment(
        readiness,
        _verification(),
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        checked_at=NOW,
    )

    assert "REGISTRY_FINGERPRINT_MISMATCH" in assessment.blockers


def test_future_verification_blocks_readiness():
    readiness = FakeEvidenceReadiness(
        complete=True,
        registry_fingerprint=FP,
        fingerprint="c" * 64,
    )
    verification = _verification()
    future_verification = replace(
        verification,
        verified_at=NOW + timedelta(seconds=1),
    )

    assessment = build_integration_execution_readiness_assessment(
        readiness,
        future_verification,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        checked_at=NOW,
    )

    assert "VERIFICATION_TIME_IN_FUTURE" in assessment.blockers


def test_candidate_mismatch_blocks_readiness():
    readiness = FakeEvidenceReadiness(
        complete=True,
        registry_fingerprint=FP,
        fingerprint="c" * 64,
    )

    assessment = build_integration_execution_readiness_assessment(
        readiness,
        _verification(),
        repository="Ali-Marandi/Morva",
        candidate_sha="e" * 40,
        checked_at=NOW,
    )

    assert "CANDIDATE_SHA_MISMATCH" in assessment.blockers


def test_assessment_fingerprint_tampering_is_rejected():
    readiness = FakeEvidenceReadiness(
        complete=True,
        registry_fingerprint=FP,
        fingerprint="c" * 64,
    )
    assessment = build_integration_execution_readiness_assessment(
        readiness,
        _verification(),
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        checked_at=NOW,
    )

    with pytest.raises(
        IntegrationExecutionReadinessAssessmentError,
        match="fingerprint mismatch",
    ):
        replace(assessment, fingerprint="f" * 64)
