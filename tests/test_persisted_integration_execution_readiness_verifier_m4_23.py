from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from morva.runtime.independent_persisted_integration_execution_readiness_verifier_m4_23 import (
    PersistedIntegrationExecutionReadinessVerificationError,
    verify_persisted_integration_execution_readiness,
)


NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
SHA = "b" * 40
EVIDENCE = "3" * 64
BINDING = "1" * 64
BINDING_VERIFICATION = "2" * 64


def _sha256(payload: dict[str, object]) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _record(**overrides):
    assessment_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "checked_at": NOW.isoformat(),
        "evidence_readiness_fingerprint": EVIDENCE,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": BINDING_VERIFICATION,
        "state": "ready",
        "blockers": [],
    }
    assessment_fingerprint = _sha256(assessment_payload)
    verification_fingerprint = _sha256(
        {
            "assessment_fingerprint": assessment_fingerprint,
            "verified_at": NOW.isoformat(),
        }
    )
    values = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "assessment_checked_at": NOW,
        "verified_at": NOW,
        "evidence_readiness_fingerprint": EVIDENCE,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": BINDING_VERIFICATION,
        "state": "ready",
        "blockers": [],
        "assessment_fingerprint": assessment_fingerprint,
        "verification_fingerprint": verification_fingerprint,
        "created_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_m4_23_independently_verifies_persisted_receipt():
    record = _record()

    verification = verify_persisted_integration_execution_readiness(
        record,
        candidate_sha=SHA,
        target_environment="staging",
    )

    assert verification.verified is True
    assert verification.repository == "Ali-Marandi/Morva"
    assert verification.candidate_sha == SHA
    assert verification.state == "ready"
    assert verification.blockers == ()


def test_m4_23_rejects_assessment_fingerprint_tampering():
    record = _record(assessment_fingerprint="f" * 64)

    with pytest.raises(
        PersistedIntegrationExecutionReadinessVerificationError,
        match="assessment fingerprint mismatch",
    ):
        verify_persisted_integration_execution_readiness(record)


def test_m4_23_rejects_verification_fingerprint_tampering():
    record = _record(verification_fingerprint="f" * 64)

    with pytest.raises(
        PersistedIntegrationExecutionReadinessVerificationError,
        match="verification fingerprint mismatch",
    ):
        verify_persisted_integration_execution_readiness(record)


@pytest.mark.parametrize(
    "overrides, pattern",
    [
        ({"assessment_version": 2}, "unsupported persisted assessment version"),
        ({"target_environment": "production"}, "persisted target environment"),
        ({"state": "ready", "blockers": ["TAMPERED"]}, "cannot contain blockers"),
        ({"state": "blocked", "blockers": []}, "must contain blockers"),
        ({"blockers": None}, "persisted blockers must be a list or tuple"),
    ],
)
def test_m4_23_fail_closed_invariant_checks(overrides, pattern):
    record = _record(**overrides)

    with pytest.raises(
        PersistedIntegrationExecutionReadinessVerificationError,
        match=pattern,
    ):
        verify_persisted_integration_execution_readiness(record)


def test_m4_23_verifies_blocked_state_without_promoting_it():
    record = _record(
        state="blocked",
        blockers=("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE",),
    )
    assessment_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "checked_at": NOW.isoformat(),
        "evidence_readiness_fingerprint": EVIDENCE,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": BINDING_VERIFICATION,
        "state": "blocked",
        "blockers": ["AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE"],
    }
    record.assessment_fingerprint = _sha256(assessment_payload)
    record.verification_fingerprint = _sha256(
        {
            "assessment_fingerprint": record.assessment_fingerprint,
            "verified_at": NOW.isoformat(),
        }
    )

    verification = verify_persisted_integration_execution_readiness(record)

    assert verification.state == "blocked"
    assert verification.verified is True


def test_m4_23_rejects_naive_persisted_timestamp():
    record = _record(assessment_checked_at=NOW.replace(tzinfo=None))

    with pytest.raises(
        PersistedIntegrationExecutionReadinessVerificationError,
        match="assessment_checked_at must be timezone-aware",
    ):
        verify_persisted_integration_execution_readiness(record)


def test_m4_23_rejects_candidate_filter_mismatch():
    record = _record()

    with pytest.raises(
        PersistedIntegrationExecutionReadinessVerificationError,
        match="persisted candidate SHA mismatch",
    ):
        verify_persisted_integration_execution_readiness(
            record,
            candidate_sha="c" * 40,
        )
