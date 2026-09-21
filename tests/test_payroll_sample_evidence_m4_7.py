from __future__ import annotations

from datetime import datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.payroll_sample_evidence import (
    PayrollSampleEvidence,
    PayrollSampleEvidenceError,
    build_payroll_sample_evidence_binding,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
SHA = "a" * 64
OUTPUT = "b" * 64
COMPARE = "c" * 64


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "SAMPLE-1405-001",
        "source_type": "payroll_sample",
        "source_uri": "https://authority.example/payroll-samples/1405-01/001",
        "source_sha256": SHA,
        "issuer": "payroll-authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "authority-approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _sample(**overrides):
    payload = {
        "evidence_version": 1,
        "sample_id": "S-001",
        "population_scope": "teachers",
        "payroll_period": "1405-01",
        "authoritative_evidence_id": "SAMPLE-1405-001",
        "input_manifest_sha256": SHA,
        "expected_output_sha256": OUTPUT,
        "comparison_fingerprint": COMPARE,
        "source_uri": "https://authority.example/payroll-samples/1405-01/001",
        "issuer": "payroll-authority",
        "reviewer_id": "reviewer",
        "approver_id": "approver",
        "reviewed_at": "2026-09-19T10:00:00+00:00",
        "approved_at": "2026-09-20T10:00:00+00:00",
    }
    payload.update(overrides)
    return PayrollSampleEvidence(**payload)


def _registry(item=None):
    return build_registry((item or _authority(),), registered_at=NOW)


def test_binding_accepts_matching_sample_evidence():
    binding = build_payroll_sample_evidence_binding(
        _sample(),
        _registry(),
        bound_by="sample-binder",
        bound_at=NOW,
    )
    assert binding.sample_id == "S-001"
    assert binding.payroll_period == "1405-01"
    assert len(binding.fingerprint) == 64


def test_hash_mismatch_is_rejected():
    with pytest.raises(PayrollSampleEvidenceError, match="input manifest"):
        build_payroll_sample_evidence_binding(
            _sample(input_manifest_sha256=OUTPUT),
            _registry(),
            bound_by="sample-binder",
            bound_at=NOW,
        )


def test_population_scope_mismatch_is_rejected():
    with pytest.raises(PayrollSampleEvidenceError, match="population scope"):
        build_payroll_sample_evidence_binding(
            _sample(),
            _registry(_authority(population_scope="staff")),
            bound_by="sample-binder",
            bound_at=NOW,
        )


def test_future_authority_approval_is_rejected():
    with pytest.raises(PayrollSampleEvidenceError, match="precedes"):
        build_payroll_sample_evidence_binding(
            _sample(),
            _registry(
                _authority(approved_at="2026-09-23T10:00:00+00:00")
            ),
            bound_by="sample-binder",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    with pytest.raises(PayrollSampleEvidenceError, match="expired"):
        build_payroll_sample_evidence_binding(
            _sample(),
            _registry(
                _authority(expires_at="2026-09-21T23:59:59+00:00")
            ),
            bound_by="sample-binder",
            bound_at=NOW,
        )


def test_invalid_period_is_rejected():
    with pytest.raises(PayrollSampleEvidenceError, match="Jalali"):
        _sample(payroll_period="2026-01")


def test_distinct_review_and_approval_is_required():
    with pytest.raises(PayrollSampleEvidenceError, match="distinct"):
        _sample(approver_id="reviewer")
