from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.evidence_role_binding_records import (
    EvidenceRoleBindingRepository,
)
from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.persistence.models import Base
from morva.runtime.evidence_submission import _fingerprint
from morva.security.policy import Scope


NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            AuthoritativeEvidenceSubmissionRecord.__table__,
        ],
    )
    # Create the binding table after imports; lifecycle dependencies are not required.
    from morva.persistence.evidence_role_binding_records import EvidenceRoleBindingRecord

    EvidenceRoleBindingRecord.__table__.create(engine)
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _submission(
    session,
    *,
    evidence_id: str,
    source_type: str = "legal_rule",
    submitted_by: str = "submitter",
    decided_by: str = "approver",
    effective_from: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
    scope_id: str = "province-1",
):
    record = AuthoritativeEvidenceSubmissionRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_uri=f"https://authority.example/{evidence_id}",
        source_sha256="a" * 64,
        issuer="authority",
        population_scope="teachers",
        submission_scope=Scope.PROVINCE.value,
        submission_scope_id=scope_id,
        effective_from=effective_from,
        effective_to=datetime(2027, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        status="accepted",
        submitted_by=submitted_by,
        submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        decided_by=decided_by,
        decided_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        fingerprint="",
    )
    record.fingerprint = _fingerprint(
        evidence_id=record.evidence_id,
        source_type=record.source_type,
        source_uri=record.source_uri,
        source_sha256=record.source_sha256,
        issuer=record.issuer,
        population_scope=record.population_scope,
        submission_scope=Scope(record.submission_scope),
        submission_scope_id=record.submission_scope_id,
        effective_from=effective_from,
        effective_to=record.effective_to,
        expires_at=record.expires_at,
        submitted_by=record.submitted_by,
        submitted_at=record.submitted_at,
    )
    session.add(record)
    session.flush()
    record.effective_from = effective_from
    record.effective_to = datetime(2027, 1, 1, tzinfo=timezone.utc)
    record.expires_at = datetime(2026, 12, 31, tzinfo=timezone.utc)
    record.submitted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record.decided_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    return record


def test_creates_role_binding_for_current_accepted_evidence(session):
    _submission(session, evidence_id="E-LEGAL")
    record = EvidenceRoleBindingRepository(session).create_binding(
        certification_role="legal_approval",
        authoritative_evidence_id="E-LEGAL",
        bound_by="binding-manager",
        bound_at=NOW,
        reason="approved legal evidence is bound",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    assert record.binding_kind == "external_approval"
    assert len(record.binding_fingerprint) == 64
    assert record.registry_fingerprint
    assert record.to_receipt().authoritative_evidence_id == "E-LEGAL"


def test_wrong_source_type_is_rejected(session):
    _submission(session, evidence_id="E-SEC", source_type="security_assessment")
    with pytest.raises(Exception, match="wrong source_type"):
        EvidenceRoleBindingRepository(session).create_binding(
            certification_role="legal_approval",
            authoritative_evidence_id="E-SEC",
            bound_by="binding-manager",
            bound_at=NOW,
            reason="wrong role",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_binding_actor_must_differ_from_submitter_and_approver(session):
    _submission(session, evidence_id="E-LEGAL")
    with pytest.raises(Exception, match="separation of duties"):
        EvidenceRoleBindingRepository(session).create_binding(
            certification_role="legal_approval",
            authoritative_evidence_id="E-LEGAL",
            bound_by="approver",
            bound_at=NOW,
            reason="same as approver",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_scope_isolation_is_enforced(session):
    _submission(session, evidence_id="E-LEGAL", scope_id="province-2")
    with pytest.raises(Exception, match="organization scope"):
        EvidenceRoleBindingRepository(session).create_binding(
            certification_role="legal_approval",
            authoritative_evidence_id="E-LEGAL",
            bound_by="binding-manager",
            bound_at=NOW,
            reason="wrong scope",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_duplicate_current_role_binding_is_rejected(session):
    _submission(session, evidence_id="E-LEGAL")
    repository = EvidenceRoleBindingRepository(session)
    repository.create_binding(
        certification_role="legal_approval",
        authoritative_evidence_id="E-LEGAL",
        bound_by="manager-one",
        bound_at=NOW,
        reason="first binding",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    with pytest.raises(Exception, match="already bound"):
        repository.create_binding(
            certification_role="legal_approval",
            authoritative_evidence_id="E-LEGAL",
            bound_by="manager-two",
            bound_at=NOW,
            reason="duplicate binding",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_two_roles_can_bind_to_same_registry(session):
    _submission(session, evidence_id="E-LEGAL")
    _submission(
        session,
        evidence_id="E-FIN",
        source_type="finance_approval",
        submitted_by="finance-submit",
    )
    repository = EvidenceRoleBindingRepository(session)
    first = repository.create_binding(
        certification_role="legal_approval",
        authoritative_evidence_id="E-LEGAL",
        bound_by="manager-one",
        bound_at=NOW,
        reason="legal role",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    second = repository.create_binding(
        certification_role="finance_approval",
        authoritative_evidence_id="E-FIN",
        bound_by="manager-two",
        bound_at=NOW,
        reason="finance role",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    assert first.registry_fingerprint == second.registry_fingerprint


def test_new_evidence_changes_registry_identity_and_allows_new_binding(session):
    _submission(session, evidence_id="E-LEGAL")
    repository = EvidenceRoleBindingRepository(session)
    first = repository.create_binding(
        certification_role="legal_approval",
        authoritative_evidence_id="E-LEGAL",
        bound_by="manager-one",
        bound_at=NOW,
        reason="initial",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    _submission(
        session,
        evidence_id="E-FIN",
        source_type="finance_approval",
        submitted_by="finance-submit",
    )
    second = repository.create_binding(
        certification_role="legal_approval",
        authoritative_evidence_id="E-LEGAL",
        bound_by="manager-two",
        bound_at=NOW,
        reason="rebinding after registry change",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )
    assert second.registry_fingerprint != first.registry_fingerprint


def test_lifecycle_api_routes_are_registered():
    from morva.api.app import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/evidence-submissions/bindings" in paths
    assert "/api/v1/evidence-submissions/bindings" in paths
