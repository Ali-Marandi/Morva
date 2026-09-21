from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.evidence_closure_matrix import CLOSURE_ROLE_SOURCE_TYPES
from morva.runtime.evidence_convergence import (
    CANONICAL_BINDING_KINDS,
    EvidenceBindingReceipt,
    EvidenceConvergenceError,
    build_convergence_assessment,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
REPO = "Ali-Marandi/Morva"


def _authority(role: str, evidence_id: str | None = None):
    source_type = {
        "authoritative_master_data": "master_data",
        "official_adapters": "adapter_contract",
        "reconciliation_evidence": "reconciliation",
        "dr_exercise": "dr_report",
        "load_validation": "load_validation",
        "security_assessment": "security_assessment",
    }.get(role, "legal_rule")
    return AuthoritativeEvidenceItem(
        intake_version=1,
        evidence_id=evidence_id or f"E-{role}",
        source_type=source_type,
        source_uri=f"https://authority.example/{role}",
        source_sha256="a" * 64,
        issuer="authority",
        population_scope="enterprise",
        effective_from="2026-01-01T00:00:00+00:00",
        effective_to="2027-01-01T00:00:00+00:00",
        status="accepted",
        approved_by="approver",
        approved_at="2026-09-20T10:00:00+00:00",
        expires_at="2026-12-31T00:00:00+00:00",
    )


def _receipt(role: str, evidence_id: str):
    return EvidenceBindingReceipt(
        receipt_version=1,
        certification_role=role,
        binding_kind=CANONICAL_BINDING_KINDS[role],
        authoritative_evidence_id=evidence_id,
        binding_fingerprint="b" * 64,
        registry_fingerprint="c" * 64,
        population_scope="enterprise",
        bound_at=NOW,
    )


def test_partial_convergence_is_fail_closed():
    registry = build_registry(
        (
            _authority("authoritative_master_data"),
            _authority("security_assessment"),
        ),
        registered_at=NOW,
    )
    receipts = (
        _receipt(
            "authoritative_master_data",
            "E-authoritative_master_data",
        ),
        _receipt("security_assessment", "E-security_assessment"),
    )
    # Replace the registry fingerprint after receipt construction.
    receipts = tuple(
        EvidenceBindingReceipt(
            receipt_version=r.receipt_version,
            certification_role=r.certification_role,
            binding_kind=r.binding_kind,
            authoritative_evidence_id=r.authoritative_evidence_id,
            binding_fingerprint=r.binding_fingerprint,
            registry_fingerprint=registry.fingerprint,
            population_scope=r.population_scope,
            bound_at=r.bound_at,
        )
        for r in receipts
    )
    assessment = build_convergence_assessment(
        registry,
        repository=REPO,
        checked_at=NOW,
        receipts=receipts,
    )
    assert not assessment.complete
    assert "official_adapters" in assessment.blocked_roles
    assert "authoritative_master_data" in assessment.satisfied_roles


def test_receipt_registry_fingerprint_mismatch_is_rejected():
    registry = build_registry(
        (_authority("security_assessment"),),
        registered_at=NOW,
    )
    with pytest.raises(EvidenceConvergenceError, match="registry fingerprint"):
        build_convergence_assessment(
            registry,
            repository=REPO,
            checked_at=NOW,
            receipts=(
                _receipt("security_assessment", "E-security_assessment"),
            ),
        )


def test_duplicate_roles_are_rejected():
    registry = build_registry(
        (_authority("security_assessment"),),
        registered_at=NOW,
    )
    role_receipt = _receipt("security_assessment", "E-security_assessment")
    role_receipt = EvidenceBindingReceipt(
        receipt_version=1,
        certification_role=role_receipt.certification_role,
        binding_kind=role_receipt.binding_kind,
        authoritative_evidence_id=role_receipt.authoritative_evidence_id,
        binding_fingerprint=role_receipt.binding_fingerprint,
        registry_fingerprint=registry.fingerprint,
        population_scope=role_receipt.population_scope,
        bound_at=role_receipt.bound_at,
    )
    with pytest.raises(EvidenceConvergenceError, match="duplicate"):
        build_convergence_assessment(
            registry,
            repository=REPO,
            checked_at=NOW,
            receipts=(role_receipt, role_receipt),
        )


def test_future_receipt_is_rejected():
    registry = build_registry(
        (_authority("security_assessment"),),
        registered_at=NOW,
    )
    receipt = _receipt("security_assessment", "E-security_assessment")
    receipt = EvidenceBindingReceipt(
        receipt_version=1,
        certification_role=receipt.certification_role,
        binding_kind=receipt.binding_kind,
        authoritative_evidence_id=receipt.authoritative_evidence_id,
        binding_fingerprint=receipt.binding_fingerprint,
        registry_fingerprint=registry.fingerprint,
        population_scope=receipt.population_scope,
        bound_at=datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
    )
    with pytest.raises(EvidenceConvergenceError, match="future-dated"):
        build_convergence_assessment(
            registry,
            repository=REPO,
            checked_at=NOW,
            receipts=(receipt,),
        )


def test_supporting_evidence_must_be_current():
    registry = build_registry(
        (_authority("security_assessment"),),
        registered_at=NOW,
    )
    receipt = _receipt("security_assessment", "E-security_assessment")
    receipt = EvidenceBindingReceipt(
        receipt_version=1,
        certification_role=receipt.certification_role,
        binding_kind=receipt.binding_kind,
        authoritative_evidence_id=receipt.authoritative_evidence_id,
        binding_fingerprint=receipt.binding_fingerprint,
        registry_fingerprint=registry.fingerprint,
        population_scope=receipt.population_scope,
        bound_at=receipt.bound_at,
    )
    with pytest.raises(EvidenceConvergenceError, match="supporting evidence"):
        build_convergence_assessment(
            registry,
            repository=REPO,
            checked_at=NOW,
            receipts=(receipt,),
            supporting_evidence_ids=("MISSING",),
        )


def test_canonical_roles_cover_all_twelve_requirements():
    assert set(CANONICAL_BINDING_KINDS) == set(CLOSURE_ROLE_SOURCE_TYPES)
