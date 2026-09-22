from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
import json

import pytest

from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
)
from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerificationError,
    verify_integration_execution_readiness_assessment,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
SHA = "b" * 40
FP = "a" * 64
BINDING = "1" * 64
VERIFICATION = "2" * 64
READINESS = "3" * 64


def _assessment(*, checked_at: datetime = NOW, blockers: tuple[str, ...] = ()) -> IntegrationExecutionReadinessAssessment:
    state = "ready" if not blockers else "blocked"
    payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "checked_at": checked_at,
        "evidence_readiness_fingerprint": READINESS,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": VERIFICATION,
        "state": state,
        "blockers": blockers,
    }
    fingerprint_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA.lower(),
        "target_environment": "staging",
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "evidence_readiness_fingerprint": READINESS.lower(),
        "binding_fingerprint": BINDING.lower(),
        "binding_verification_fingerprint": VERIFICATION.lower(),
        "state": state,
        "blockers": list(blockers),
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return IntegrationExecutionReadinessAssessment(
        fingerprint=fingerprint,
        **payload,
    )


def _write(path, assessment, *, ready_override=None, fingerprint_override=None):
    payload = assessment.to_payload()
    if ready_override is not None:
        payload["ready"] = ready_override
    if fingerprint_override is not None:
        payload["fingerprint"] = fingerprint_override
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


def test_independently_verifies_ready_assessment(tmp_path):
    path = tmp_path / "assessment.json"
    assessment = _assessment()
    _write(path, assessment)

    verification = verify_integration_execution_readiness_assessment(
        path,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        verified_at=NOW,
    )

    assert verification.assessment == assessment
    assert len(verification.fingerprint) == 64


def test_blocked_assessment_is_verified_without_being_promoted():
    assessment = _assessment(
        blockers=("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE",),
    )
    assert assessment.state == "blocked"
    assert not assessment.ready


def test_fingerprint_tampering_is_rejected(tmp_path):
    path = tmp_path / "assessment.json"
    _write(path, _assessment(), fingerprint_override="f" * 64)

    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="assessment structure is invalid|fingerprint mismatch",
    ):
        verify_integration_execution_readiness_assessment(
            path,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            verified_at=NOW,
        )


def test_ready_flag_tampering_is_rejected(tmp_path):
    path = tmp_path / "assessment.json"
    _write(path, _assessment(), ready_override=False)

    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="ready flag mismatch|assessment structure is invalid",
    ):
        verify_integration_execution_readiness_assessment(
            path,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            verified_at=NOW,
        )


def test_repository_mismatch_is_rejected(tmp_path):
    path = tmp_path / "assessment.json"
    _write(path, _assessment())

    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="repository mismatch",
    ):
        verify_integration_execution_readiness_assessment(
            path,
            repository="other/repository",
            candidate_sha=SHA,
            verified_at=NOW,
        )


def test_candidate_sha_mismatch_is_rejected(tmp_path):
    path = tmp_path / "assessment.json"
    _write(path, _assessment())

    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="candidate SHA mismatch",
    ):
        verify_integration_execution_readiness_assessment(
            path,
            repository="Ali-Marandi/Morva",
            candidate_sha="c" * 40,
            verified_at=NOW,
        )


def test_verification_before_assessment_check_is_rejected(tmp_path):
    path = tmp_path / "assessment.json"
    assessment = _assessment()
    _write(path, assessment)

    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="precedes assessment check time",
    ):
        verify_integration_execution_readiness_assessment(
            path,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            verified_at=NOW - timedelta(seconds=1),
        )
