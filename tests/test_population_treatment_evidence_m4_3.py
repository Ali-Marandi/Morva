from __future__ import annotations

from datetime import datetime

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.rules.population_treatment_evidence import (
    REQUIRED_1405_COMPONENTS,
    PopulationTreatmentEvidence,
    PopulationTreatmentEvidenceError,
    build_treatment_set,
)


NOW = datetime.fromisoformat("2026-09-22T10:00:00+00:00")
SHA = "a" * 64


def _authority(**overrides) -> AuthoritativeEvidenceItem:
    payload = {
        "intake_version": 1,
        "evidence_id": "LEGAL-001",
        "source_type": "legal_rule",
        "source_uri": "https://authority.example/legal/1405",
        "source_sha256": SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "legal-approver",
        "approved_at": "2026-09-20T00:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _treatment(component_code: str, **overrides) -> PopulationTreatmentEvidence:
    payload = {
        "evidence_version": 1,
        "component_code": component_code,
        "population_scope": "teachers",
        "authoritative_evidence_id": "LEGAL-001",
        "treatment": "earning" if component_code not in {"TAX", "LOAN", "COURT_ORDER"} else "deduction",
        "taxable": component_code in {"JOB_RIGHT", "OVERTIME"},
        "pensionable": component_code in {"JOB_RIGHT", "RANK_ALLOWANCE"},
        "insurable": component_code in {"JOB_RIGHT", "RANK_ALLOWANCE"},
        "reviewer_id": "treatment-reviewer",
        "approver_id": "treatment-approver",
        "reviewed_at": "2026-09-19T10:00:00+00:00",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "status": "approved",
    }
    payload.update(overrides)
    return PopulationTreatmentEvidence(**payload)


def _registry(item: AuthoritativeEvidenceItem):
    return build_registry((item,), registered_at=NOW)


def test_complete_1405_population_treatment_is_activation_ready():
    authority = _authority()
    registry = _registry(authority)
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    assert treatment_set.is_activation_ready(
        registry,
        checked_at=NOW,
    )
    assert treatment_set.activation_blockers(registry, checked_at=NOW) == ()
    assert len(treatment_set.fingerprint) == 64


def test_missing_component_is_fail_closed():
    registry = _registry(_authority())
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS[:-1]),
        registered_at=NOW,
    )
    blockers = treatment_set.activation_blockers(registry, checked_at=NOW)
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert "missing population treatment for component COURT_ORDER" in blockers


def test_wrong_authority_source_type_is_fail_closed():
    registry = _registry(_authority(source_type="master_data"))
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert any("not bound to legal-rule evidence" in blocker for blocker in treatment_set.activation_blockers(registry, checked_at=NOW))


def test_unaccepted_authority_is_fail_closed():
    registry = _registry(
        _authority(
            status="pending",
            approved_by=None,
            approved_at=None,
        )
    )
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    blockers = treatment_set.activation_blockers(registry, checked_at=NOW)
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert any("not accepted" in blocker for blocker in blockers)


def test_population_scope_mismatch_is_fail_closed():
    registry = _registry(_authority(population_scope="teachers"))
    treatment_set = build_treatment_set(
        tuple(
            _treatment(
                code,
                population_scope="school_support",
            )
            for code in REQUIRED_1405_COMPONENTS
        ),
        registered_at=NOW,
    )
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert any("population scope mismatch" in blocker for blocker in treatment_set.activation_blockers(registry, checked_at=NOW))


def test_expired_authority_is_fail_closed():
    registry = _registry(
        _authority(expires_at="2026-09-21T23:59:59+00:00")
    )
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert any("expired" in blocker for blocker in treatment_set.activation_blockers(registry, checked_at=NOW))


def test_future_authority_approval_is_fail_closed():
    registry = _registry(
        _authority(approved_at="2026-09-23T10:00:00+00:00")
    )
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
    assert any("approval is not effective" in blocker for blocker in treatment_set.activation_blockers(registry, checked_at=NOW))


def test_treatment_review_and_approval_actors_must_differ():
    with pytest.raises(
        PopulationTreatmentEvidenceError,
        match="reviewer and approver",
    ):
        _treatment(
            REQUIRED_1405_COMPONENTS[0],
            approver_id="treatment-reviewer",
        )


def test_authority_effective_from_future_is_fail_closed():
    registry = _registry(
        _authority(
            effective_from="2026-09-23T00:00:00+00:00",
            effective_to="2027-01-01T00:00:00+00:00",
        )
    )
    treatment_set = build_treatment_set(
        tuple(_treatment(code) for code in REQUIRED_1405_COMPONENTS),
        registered_at=NOW,
    )
    assert not treatment_set.is_activation_ready(registry, checked_at=NOW)
