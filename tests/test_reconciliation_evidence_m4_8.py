from __future__ import annotations

from datetime import datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.reconciliation_evidence import (
    ReconciliationEvidenceError,
    ThreeWayReconciliationEvidence,
    build_three_way_reconciliation_binding,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
AUTH_SHA = "a" * 64
ENTITLEMENT = "b" * 64
TREASURY = "c" * 64
BANK = "d" * 64
COMPARE = AUTH_SHA


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "RECON-001",
        "source_type": "reconciliation",
        "source_uri": "https://authority.example/reconciliation/1405-01",
        "source_sha256": AUTH_SHA,
        "issuer": "reconciliation-authority",
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


def _evidence(**overrides):
    payload = {
        "evidence_version": 1,
        "reconciliation_id": "R-001",
        "population_scope": "teachers",
        "payroll_period": "1405-01",
        "authoritative_evidence_id": "RECON-001",
        "morva_entitlement_sha256": ENTITLEMENT,
        "treasury_instruction_sha256": TREASURY,
        "bank_settlement_sha256": BANK,
        "comparison_fingerprint": COMPARE,
        "reconciliation_status": "reconciled",
        "reviewer_id": "reviewer",
        "approver_id": "approver",
        "reviewed_at": "2026-09-20T10:00:00+00:00",
        "approved_at": "2026-09-21T10:00:00+00:00",
    }
    payload.update(overrides)
    return ThreeWayReconciliationEvidence(**payload)


def _registry(item=None):
    return build_registry((item or _authority(),), registered_at=NOW)


def test_reconciled_three_way_binding_is_created():
    binding = build_three_way_reconciliation_binding(
        _evidence(),
        _registry(),
        bound_by="reconciliation-binder",
        bound_at=NOW,
    )
    assert binding.reconciliation_id == "R-001"
    assert binding.morva_entitlement_sha256 == ENTITLEMENT
    assert binding.treasury_instruction_sha256 == TREASURY
    assert binding.bank_settlement_sha256 == BANK
    assert len(binding.fingerprint) == 64


def test_non_reconciled_status_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="reconciled"):
        _evidence(reconciliation_status="mismatch")


def test_hash_mismatch_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="comparison fingerprint"):
        build_three_way_reconciliation_binding(
            _evidence(comparison_fingerprint="e" * 64),
            _registry(),
            bound_by="reconciliation-binder",
            bound_at=NOW,
        )


def test_scope_mismatch_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="population scope"):
        build_three_way_reconciliation_binding(
            _evidence(),
            _registry(_authority(population_scope="staff")),
            bound_by="reconciliation-binder",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="expired"):
        build_three_way_reconciliation_binding(
            _evidence(),
            _registry(_authority(expires_at="2026-09-21T23:59:59+00:00")),
            bound_by="reconciliation-binder",
            bound_at=NOW,
        )


def test_future_authority_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="not yet effective"):
        build_three_way_reconciliation_binding(
            _evidence(),
            _registry(
                _authority(
                    effective_from="2026-09-23T00:00:00+00:00",
                    effective_to="2027-01-01T00:00:00+00:00",
                )
            ),
            bound_by="reconciliation-binder",
            bound_at=NOW,
        )


def test_review_and_approval_actors_must_differ():
    with pytest.raises(ReconciliationEvidenceError, match="distinct"):
        _evidence(approver_id="reviewer")


def test_duplicate_artifact_hashes_are_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="independently"):
        _evidence(treasury_instruction_sha256=ENTITLEMENT)


def test_invalid_jalali_period_is_rejected():
    with pytest.raises(ReconciliationEvidenceError, match="Jalali"):
        _evidence(payroll_period="2026-01")
