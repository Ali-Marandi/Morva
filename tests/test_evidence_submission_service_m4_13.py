from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from morva.persistence.models import Base
from morva.runtime.evidence_submission import (
    EvidenceSubmissionError,
    decide_evidence,
    submit_evidence,
    verify_submission_record,
)
from morva.security.policy import Scope

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
SHA = "a" * 64


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine, tables=[AuthoritativeEvidenceSubmissionRecord.__table__])
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _submit(session, **overrides):
    values = {
        "evidence_id": "EVID-001",
        "source_type": "legal_rule",
        "source_uri": "https://authority.example/evidence/1",
        "source_sha256": SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "submission_scope": Scope.PROVINCE,
        "submission_scope_id": "province-1",
        "effective_from": NOW,
        "effective_to": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2026, 12, 31, tzinfo=timezone.utc),
        "submitted_by": "submitter",
        "submitted_at": NOW,
    }
    values.update(overrides)
    return submit_evidence(session, **values)


def test_submission_is_pending_and_fingerprinted(session):
    record = _submit(session)
    assert record.status == "pending"
    assert len(record.fingerprint) == 64
    assert record.decided_by is None
    assert record.submission_scope == Scope.PROVINCE.value
    assert record.submission_scope_id == "province-1"
    assert len(record.fingerprint) == 64


def test_duplicate_evidence_id_is_rejected(session):
    _submit(session)
    with pytest.raises(EvidenceSubmissionError, match="already submitted"):
        _submit(session)


def test_unsupported_source_type_is_rejected(session):
    with pytest.raises(EvidenceSubmissionError, match="unsupported"):
        _submit(session, source_type="unknown")


def test_invalid_hash_is_rejected(session):
    with pytest.raises(EvidenceSubmissionError, match="SHA-256"):
        _submit(session, source_sha256="bad")


def test_invalid_window_is_rejected(session):
    with pytest.raises(EvidenceSubmissionError, match="effective_to"):
        _submit(session, effective_to=NOW)


def test_acceptance_requires_distinct_actor(session):
    record = _submit(session)
    with pytest.raises(Exception, match="distinct"):
        decide_evidence(
            session,
            evidence_id=record.evidence_id,
            approver_id=record.submitted_by,
            decision="accepted",
            decided_at=NOW,
        )


def test_acceptance_is_one_way_from_pending(session):
    record = _submit(session)
    decided = decide_evidence(
        session,
        evidence_id=record.evidence_id,
        approver_id="approver",
        decision="accepted",
        decided_at=NOW,
    )
    assert decided.status == "accepted"
    assert decided.decided_by == "approver"
    assert decided.decided_at is not None
    with pytest.raises(EvidenceSubmissionError, match="pending"):
        decide_evidence(
            session,
            evidence_id=record.evidence_id,
            approver_id="approver-2",
            decision="rejected",
            decided_at=NOW,
            rejection_reason="late",
        )


def test_persisted_pending_record_verifies_cleanly(session):
    record = _submit(session)
    verify_submission_record(record)


def test_persisted_accepted_record_verifies_cleanly(session):
    record = _submit(session)
    decide_evidence(
        session,
        evidence_id=record.evidence_id,
        approver_id="approver",
        decision="accepted",
        decided_at=NOW,
    )
    verify_submission_record(record)


def test_persisted_fingerprint_mutation_is_detected(session):
    record = _submit(session)
    record.source_uri = "https://attacker.example/changed"
    with pytest.raises(EvidenceSubmissionError, match="fingerprint"):
        verify_submission_record(record)
