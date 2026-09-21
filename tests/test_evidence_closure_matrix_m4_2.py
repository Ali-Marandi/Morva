from __future__ import annotations

from datetime import datetime
import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.evidence_closure_matrix import (
    CANONICAL_REQUIREMENTS,
    CLOSURE_ROLE_SOURCE_TYPES,
    EvidenceClosureMatrixError,
    evaluate_closure,
)


NOW = datetime.fromisoformat("2026-09-22T10:00:00+00:00")
SHA = "a" * 64
REPOSITORY = "Ali-Marandi/Morva"


def _item(role: str, *, evidence_id: str | None = None, **overrides):
    source_type = CLOSURE_ROLE_SOURCE_TYPES[role][0]
    payload = {
        "intake_version": 1,
        "evidence_id": evidence_id or f"E-{role}",
        "source_type": source_type,
        "source_uri": f"https://authority.example/{role}",
        "source_sha256": SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "approver",
        "approved_at": "2026-09-20T00:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def test_canonical_requirements_cover_all_roles():
    assert tuple(item.role for item in CANONICAL_REQUIREMENTS) == tuple(
        CLOSURE_ROLE_SOURCE_TYPES
    )


def test_empty_registry_cannot_be_evaluated():
    with pytest.raises(EvidenceClosureMatrixError):
        from morva.runtime.authoritative_evidence_intake import (
            AuthoritativeEvidenceRegistry,
        )

        evaluate_closure(
            AuthoritativeEvidenceRegistry(
                registry_version=1,
                items=(),
                registered_at=NOW,
            ),
            repository=REPOSITORY,
            checked_at=NOW,
        )


def test_partial_registry_is_fail_closed():
    registry = build_registry(
        (
            _item("legal_approval"),
            _item("security_assessment"),
        ),
        registered_at=NOW,
    )
    assessment = evaluate_closure(
        registry,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert "legal_approval" in assessment.satisfied_roles
    assert "security_assessment" in assessment.satisfied_roles
    assert len(assessment.blocked_roles) == len(CLOSURE_ROLE_SOURCE_TYPES) - 2
    assert not assessment.complete


def test_complete_registry_is_complete():
    items = tuple(
        _item(role)
        for role in CLOSURE_ROLE_SOURCE_TYPES
    )
    registry = build_registry(items, registered_at=NOW)
    assessment = evaluate_closure(
        registry,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert assessment.complete
    assert assessment.blocked_roles == ()
    assert assessment.satisfied_roles == tuple(CLOSURE_ROLE_SOURCE_TYPES)
    assert len(assessment.fingerprint) == 64


def test_wrong_source_type_does_not_satisfy_role():
    legal = _item("legal_approval", source_type="master_data")
    registry = build_registry((legal,), registered_at=NOW)
    assessment = evaluate_closure(
        registry,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert "legal_approval" in assessment.blocked_roles


def test_expired_evidence_does_not_satisfy_role():
    item = _item(
        "legal_approval",
        expires_at="2026-09-21T23:59:59+00:00",
    )
    registry = build_registry((item,), registered_at=NOW)
    assessment = evaluate_closure(
        registry,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert "legal_approval" in assessment.blocked_roles


def test_future_approved_evidence_does_not_satisfy_role():
    item = _item(
        "legal_approval",
        approved_at="2026-09-23T10:00:00+00:00",
    )
    registry = build_registry((item,), registered_at=NOW)
    assessment = evaluate_closure(
        registry,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert "legal_approval" in assessment.blocked_roles


def test_registry_fingerprint_is_bound_to_assessment():
    legal = _item("legal_approval")
    security = _item("security_assessment")
    first = build_registry((legal, security), registered_at=NOW)
    second = build_registry(
        (
            _item("legal_approval"),
            _item("security_assessment", evidence_id="E-security-2"),
        ),
        registered_at=NOW,
    )
    first_assessment = evaluate_closure(
        first,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    second_assessment = evaluate_closure(
        second,
        repository=REPOSITORY,
        checked_at=NOW,
    )
    assert first_assessment.registry_fingerprint != second_assessment.registry_fingerprint
    assert first_assessment.fingerprint != second_assessment.fingerprint
