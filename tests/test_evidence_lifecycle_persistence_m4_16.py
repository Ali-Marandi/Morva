from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.evidence_lifecycle_records import (
    AuthoritativeEvidenceLifecycleEventRecord,
    EvidenceLifecycleRepository,
)
from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.persistence.models import Base
from morva.runtime.evidence_submission import _fingerprint
from morva.security.policy import Scope


NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            AuthoritativeEvidenceSubmissionRecord.__table__,
            AuthoritativeEvidenceLifecycleEventRecord.__table__,
        ],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _submission(
    session,
    *,
    evidence_id: str,
    effective_from: datetime,
    source_type: str = "legal_rule",
    population_scope: str = "teachers",
    status: str = "accepted",
    submitted_by: str = "submitter",
    decided_by: str = "approver",
):
    record = AuthoritativeEvidenceSubmissionRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_uri=f"https://authority.example/{evidence_id}",
        source_sha256="a" * 64,
        issuer="authority",
        population_scope=population_scope,
        submission_scope=Scope.PROVINCE.value,
        submission_scope_id="province-1",
        effective_from=effective_from,
        effective_to=datetime(2027, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        status=status,
        submitted_by=submitted_by,
        submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        decided_by=decided_by if status != "pending" else None,
        decided_at=datetime(2026, 1, 2, tzinfo=timezone.utc) if status != "pending" else None,
        rejection_reason="rejected" if status == "rejected" else None,
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
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        expires_at=record.expires_at,
        submitted_by=record.submitted_by,
        submitted_at=record.submitted_at,
    )
    session.add(record)
    session.flush()
    return record


def test_persists_valid_lifecycle_link(session):
    _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _submission(
        session,
        evidence_id="E-NEW",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        submitted_by="new-submitter",
    )

    repository = EvidenceLifecycleRepository(session)
    event = repository.create_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="lifecycle-admin",
        linked_at=NOW,
        reason="renewed authoritative source",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )

    assert event.fingerprint
    assert len(event.fingerprint) == 64
    assert event.predecessor_evidence_id == "E-OLD"
    assert event.successor_evidence_id == "E-NEW"
    assert event.to_link().expected_fingerprint == event.fingerprint


def test_actor_must_differ_from_successor_submitter(session):
    _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _submission(
        session,
        evidence_id="E-NEW",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        submitted_by="new-submitter",
    )
    with pytest.raises(Exception, match="separation of duties"):
        EvidenceLifecycleRepository(session).create_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW",
            linked_by="new-submitter",
            linked_at=NOW,
            reason="bad actor",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_duplicate_predecessor_is_rejected(session):
    _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _submission(
        session,
        evidence_id="E-NEW-A",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        submitted_by="new-a",
    )
    _submission(
        session,
        evidence_id="E-NEW-B",
        effective_from=datetime(2026, 7, 1, tzinfo=timezone.utc),
        submitted_by="new-b",
    )

    repository = EvidenceLifecycleRepository(session)
    repository.create_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW-A",
        linked_by="lifecycle-admin",
        linked_at=NOW,
        reason="renewed",
        principal_scope=Scope.PROVINCE,
        principal_scope_id="province-1",
    )

    with pytest.raises(Exception):
        repository.create_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW-B",
            linked_by="lifecycle-admin-2",
            linked_at=NOW,
            reason="branched",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_scope_isolation_is_enforced(session):
    old = _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    new = _submission(
        session,
        evidence_id="E-NEW",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        submitted_by="new-submitter",
    )
    old.submission_scope_id = "province-2"
    new.submission_scope_id = "province-2"
    session.flush()

    with pytest.raises(Exception, match="principal scope"):
        EvidenceLifecycleRepository(session).create_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW",
            linked_by="lifecycle-admin",
            linked_at=NOW,
            reason="wrong scope",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_mismatched_source_type_is_rejected(session):
    _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _submission(
        session,
        evidence_id="E-NEW",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        source_type="security_assessment",
        submitted_by="new-submitter",
    )
    with pytest.raises(Exception, match="source_type"):
        EvidenceLifecycleRepository(session).create_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW",
            linked_by="lifecycle-admin",
            linked_at=NOW,
            reason="wrong source family",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )


def test_tampered_submission_is_fail_closed(session):
    old = _submission(
        session,
        evidence_id="E-OLD",
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _submission(
        session,
        evidence_id="E-NEW",
        effective_from=datetime(2026, 6, 1, tzinfo=timezone.utc),
        submitted_by="new-submitter",
    )
    old.source_uri = "https://attacker.example/tampered"
    with pytest.raises(Exception, match="verification failed"):
        EvidenceLifecycleRepository(session).create_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW",
            linked_by="lifecycle-admin",
            linked_at=NOW,
            reason="tampered source",
            principal_scope=Scope.PROVINCE,
            principal_scope_id="province-1",
        )
