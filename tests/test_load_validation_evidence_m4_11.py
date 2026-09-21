from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.load_validation_evidence import (
    LoadValidationEvidence,
    LoadValidationEvidenceError,
    build_load_validation_binding,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def _evidence(**overrides):
    values = {
        "evidence_version": 1,
        "validation_id": "LOAD-1405-001",
        "environment": "staging",
        "workload_profile": "payroll-10k",
        "population_scope": "teachers",
        "target_employees": 10_000,
        "processed_employees": 10_000,
        "elapsed_seconds": 120.5,
        "throughput_per_second": 82.9875,
        "result_fingerprint": "a" * 64,
        "authoritative_evidence_id": "LOAD-AUTH-001",
        "reviewer_id": "reviewer",
        "approver_id": "approver",
        "tested_at": "2026-09-20T10:00:00+00:00",
        "approved_at": "2026-09-21T10:00:00+00:00",
    }
    values.update(overrides)
    return LoadValidationEvidence(**values)


def _authority(evidence=None, **overrides):
    evidence = evidence or _evidence()
    values = {
        "intake_version": 1,
        "evidence_id": "LOAD-AUTH-001",
        "source_type": "load_validation",
        "source_uri": "https://authority.example/load/1405",
        "source_sha256": evidence.fingerprint,
        "issuer": "load-authority",
        "population_scope": evidence.population_scope,
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "authority-approver",
        "approved_at": "2026-09-21T09:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    values.update(overrides)
    return AuthoritativeEvidenceItem(**values)


def test_matching_load_evidence_binds():
    evidence = _evidence()
    binding = build_load_validation_binding(
        evidence,
        build_registry((_authority(evidence),), registered_at=NOW),
        bound_by="binder",
        bound_at=NOW,
    )
    assert binding.target_employees == 10_000
    assert binding.processed_employees == 10_000
    assert binding.throughput_per_second > 0
    assert len(binding.fingerprint) == 64


def test_non_staging_environment_is_rejected():
    with pytest.raises(LoadValidationEvidenceError, match="staging or pilot"):
        _evidence(environment="production")


def test_inconsistent_throughput_is_rejected():
    with pytest.raises(LoadValidationEvidenceError, match="inconsistent"):
        _evidence(throughput_per_second=10.0)


def test_short_target_is_rejected():
    with pytest.raises(LoadValidationEvidenceError, match="10000"):
        _evidence(target_employees=9999, processed_employees=9999)


def test_partial_processing_is_rejected():
    with pytest.raises(LoadValidationEvidenceError, match="processed_employees"):
        _evidence(processed_employees=9990)


def test_nonpassed_status_is_rejected():
    with pytest.raises(LoadValidationEvidenceError, match="passed"):
        _evidence(status="failed")


def test_wrong_authority_type_is_rejected():
    evidence = _evidence()
    with pytest.raises(LoadValidationEvidenceError, match="load_validation"):
        build_load_validation_binding(
            evidence,
            build_registry(
                (_authority(evidence, source_type="reconciliation"),),
                registered_at=NOW,
            ),
            bound_by="binder",
            bound_at=NOW,
        )


def test_digest_mismatch_is_rejected():
    evidence = _evidence()
    with pytest.raises(LoadValidationEvidenceError, match="fingerprint"):
        build_load_validation_binding(
            evidence,
            build_registry(
                (_authority(evidence, source_sha256="b" * 64),),
                registered_at=NOW,
            ),
            bound_by="binder",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    evidence = _evidence()
    with pytest.raises(LoadValidationEvidenceError, match="expired"):
        build_load_validation_binding(
            evidence,
            build_registry(
                (_authority(evidence, expires_at="2026-09-21T23:59:59+00:00"),),
                registered_at=NOW,
            ),
            bound_by="binder",
            bound_at=NOW,
        )
