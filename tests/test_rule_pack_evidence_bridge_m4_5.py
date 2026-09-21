from __future__ import annotations

from datetime import date, datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.rules.rule_pack_1405_evidence import RuleComponentEvidence
from morva.rules.rule_pack_evidence_bridge import (
    RulePackEvidenceBridgeError,
    build_rule_pack_evidence_binding,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")
SHA = "a" * 64
RULE_SHA = "b" * 64


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "LEGAL-TAX-001",
        "source_type": "legal_rule",
        "source_uri": "https://authority.example/legal/1405/tax",
        "source_sha256": RULE_SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "legal-approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _rule(**overrides):
    payload = {
        "component_code": "TAX",
        "source_id": "LEGAL-TAX-001",
        "citation": "official-source-section",
        "issuer": "authority",
        "source_uri": "https://authority.example/legal/1405/tax",
        "document_hash": RULE_SHA,
        "adoption_date": date(2026, 1, 1),
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2027, 1, 1),
        "retrieved_at": NOW,
        "reviewer_id": "legal-reviewer",
        "approver_id": "legal-approver-2",
        "regression_reference": "case-tax",
        "treatment": "deduction",
        "taxable": True,
        "pensionable": False,
        "insurable": False,
        "activation_status": "review_required",
    }
    payload.update(overrides)
    return RuleComponentEvidence(**payload)


def _registry(*items):
    return build_registry(tuple(items), registered_at=NOW)


def test_binding_accepts_matching_authoritative_legal_evidence():
    binding = build_rule_pack_evidence_binding(
        _rule(),
        _registry(_authority()),
        population_scope="teachers",
        authoritative_evidence_id="LEGAL-TAX-001",
        bound_by="bridge-actor",
        bound_at=NOW,
    )
    assert binding.component_code == "TAX"
    assert binding.document_hash == RULE_SHA
    assert len(binding.fingerprint) == 64


def test_missing_authority_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="not present"):
        build_rule_pack_evidence_binding(
            _rule(),
            _registry(
                _authority(evidence_id="LEGAL-OTHER-001")
            ),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_hash_mismatch_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="document hash"):
        build_rule_pack_evidence_binding(
            _rule(document_hash=SHA),
            _registry(_authority()),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_source_identity_mismatch_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="source URI"):
        build_rule_pack_evidence_binding(
            _rule(source_uri="https://other.example/legal"),
            _registry(_authority()),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_scope_mismatch_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="population scope"):
        build_rule_pack_evidence_binding(
            _rule(),
            _registry(_authority(population_scope="support")),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_future_approval_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="approval"):
        build_rule_pack_evidence_binding(
            _rule(),
            _registry(
                _authority(approved_at="2026-09-23T10:00:00+00:00")
            ),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_expired_evidence_is_rejected():
    with pytest.raises(RulePackEvidenceBridgeError, match="expired"):
        build_rule_pack_evidence_binding(
            _rule(),
            _registry(
                _authority(expires_at="2026-09-21T23:59:59+00:00")
            ),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_activation_status_is_still_fail_closed():
    with pytest.raises(RulePackEvidenceBridgeError, match="review_required"):
        build_rule_pack_evidence_binding(
            _rule(activation_status="active"),
            _registry(_authority()),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )


def test_distinct_reviewer_and_approver_are_required():
    with pytest.raises(RulePackEvidenceBridgeError, match="distinct"):
        build_rule_pack_evidence_binding(
            _rule(approver_id="legal-reviewer"),
            _registry(_authority()),
            population_scope="teachers",
            authoritative_evidence_id="LEGAL-TAX-001",
            bound_by="bridge-actor",
            bound_at=NOW,
        )
