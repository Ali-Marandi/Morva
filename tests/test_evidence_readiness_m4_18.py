from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.evidence_convergence import (
    EvidenceBindingReceipt,
    build_convergence_assessment,
)
from morva.runtime.evidence_lifecycle import build_lifecycle_assessment, build_lifecycle_link
from morva.runtime.evidence_readiness import (
    EvidenceReadinessError,
    build_readiness_assessment,
)


NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


def _item(
    evidence_id: str,
    *,
    source_type: str,
    population_scope: str = "teachers",
    effective_from: str = "2026-01-01T00:00:00+00:00",
) -> AuthoritativeEvidenceItem:
    return AuthoritativeEvidenceItem(
        intake_version=1,
        evidence_id=evidence_id,
        source_type=source_type,
        source_uri=f"https://authority.example/{evidence_id}",
        source_sha256="a" * 64,
        issuer="authority",
        population_scope=population_scope,
        effective_from=effective_from,
        effective_to="2027-01-01T00:00:00+00:00",
        status="accepted",
        approved_by="approver",
        approved_at="2026-09-01T00:00:00+00:00",
        expires_at="2026-12-31T00:00:00+00:00",
    )


def _receipt(role: str, evidence_id: str, registry_fingerprint: str) -> EvidenceBindingReceipt:
    return EvidenceBindingReceipt(
        receipt_version=1,
        certification_role=role,
        binding_kind={
            "legal_approval": "external_approval",
            "finance_approval": "external_approval",
        }[role],
        authoritative_evidence_id=evidence_id,
        binding_fingerprint="b" * 64,
        registry_fingerprint=registry_fingerprint,
        population_scope="teachers",
        bound_at=NOW,
    )


def test_missing_role_binding_produces_remediation():
    registry = build_registry(
        (_item("E-LEGAL", source_type="legal_rule"),),
        registered_at=NOW,
    )
    convergence = build_convergence_assessment(
        registry,
        repository="repo",
        checked_at=NOW,
        receipts=(),
    )
    assessment = build_readiness_assessment(
        registry,
        convergence,
        repository="repo",
        checked_at=NOW,
        receipts=(),
    )
    assert "legal_approval" in assessment.blocked_roles
    remediation = next(
        item for item in assessment.remediation if item.role == "legal_approval"
    )
    assert remediation.reason_code == "MISSING_BINDING"


def test_bound_role_is_ready():
    registry = build_registry(
        (_item("E-LEGAL", source_type="legal_rule"),),
        registered_at=NOW,
    )
    receipt = _receipt("legal_approval", "E-LEGAL", registry.fingerprint)
    convergence = build_convergence_assessment(
        registry,
        repository="repo",
        checked_at=NOW,
        receipts=(receipt,),
    )
    assessment = build_readiness_assessment(
        registry,
        convergence,
        repository="repo",
        checked_at=NOW,
        receipts=(receipt,),
    )
    assert assessment.ready_roles == ("legal_approval",)


def test_superseded_evidence_is_blocked_even_when_binding_exists():
    old = _item("E-OLD", source_type="legal_rule")
    new = _item(
        "E-NEW",
        source_type="legal_rule",
        effective_from="2026-09-02T00:00:00+00:00",
    )
    registry = build_registry((old, new), registered_at=NOW)
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="admin",
        linked_at=NOW,
        reason="renewed",
    )
    lifecycle = build_lifecycle_assessment(
        registry,
        repository="repo",
        checked_at=NOW,
        links=(link,),
    )
    receipt = _receipt("legal_approval", "E-OLD", registry.fingerprint)
    convergence = build_convergence_assessment(
        registry,
        repository="repo",
        checked_at=NOW,
        receipts=(receipt,),
    )
    assessment = build_readiness_assessment(
        registry,
        convergence,
        repository="repo",
        checked_at=NOW,
        receipts=(receipt,),
        lifecycle=lifecycle,
    )
    assert "legal_approval" in assessment.blocked_roles
    remediation = next(
        item
        for item in assessment.remediation
        if item.role == "legal_approval"
    )
    assert remediation.reason_code == "EVIDENCE_SUPERSEDED"


def test_assessment_fingerprint_tampering_is_rejected():
    registry = build_registry(
        (_item("E-LEGAL", source_type="legal_rule"),),
        registered_at=NOW,
    )
    convergence = build_convergence_assessment(
        registry,
        repository="repo",
        checked_at=NOW,
        receipts=(),
    )
    assessment = build_readiness_assessment(
        registry,
        convergence,
        repository="repo",
        checked_at=NOW,
        receipts=(),
    )
    with pytest.raises(
        EvidenceReadinessError,
        match="fingerprint mismatch",
    ):
        replace(assessment, fingerprint="f" * 64)


def test_registry_mismatch_is_rejected():
    registry = build_registry((_item("E-LEGAL", source_type="legal_rule"),), registered_at=NOW)
    other = build_registry((_item("E-OTHER", source_type="legal_rule"),), registered_at=NOW)
    convergence = build_convergence_assessment(
        other,
        repository="repo",
        checked_at=NOW,
        receipts=(),
    )
    try:
        build_readiness_assessment(
            registry,
            convergence,
            repository="repo",
            checked_at=NOW,
            receipts=(),
        )
    except EvidenceReadinessError as exc:
        assert "current registry" in str(exc)
    else:
        raise AssertionError("expected registry mismatch")
