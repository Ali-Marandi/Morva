from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRecord,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.persistence.models import Base
from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
)
from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
)


NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
SHA = "b" * 40
EVIDENCE = "3" * 64
BINDING = "1" * 64
BINDING_VERIFICATION = "2" * 64


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[IntegrationExecutionReadinessVerificationRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _verified(
    *,
    checked_at: datetime = NOW,
    state: str = "ready",
    blockers: tuple[str, ...] = (),
) -> IndependentIntegrationExecutionReadinessVerification:
    payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "checked_at": checked_at,
        "evidence_readiness_fingerprint": EVIDENCE,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": BINDING_VERIFICATION,
        "state": state,
        "blockers": blockers,
    }
    fingerprint_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": SHA,
        "target_environment": "staging",
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "evidence_readiness_fingerprint": EVIDENCE,
        "binding_fingerprint": BINDING,
        "binding_verification_fingerprint": BINDING_VERIFICATION,
        "state": state,
        "blockers": list(blockers),
    }
    fingerprint = sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assessment = IntegrationExecutionReadinessAssessment(
        fingerprint=fingerprint,
        **payload,
    )
    return IndependentIntegrationExecutionReadinessVerification(
        assessment=assessment,
        verified_at=checked_at,
    )


def test_persists_and_reloads_independently_verified_receipt(session):
    verification = _verified()
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    record = repository.record(verification)
    session.commit()

    loaded = repository.latest(
        candidate_sha=SHA,
        target_environment="staging",
    )
    assert loaded is not None
    assert loaded.id == record.id
    assert loaded.to_verification() == verification
    assert loaded.assessment_fingerprint == verification.assessment.fingerprint
    assert loaded.verification_fingerprint == verification.fingerprint


def test_duplicate_verification_is_idempotent_by_fingerprint(session):
    verification = _verified()
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    first = repository.record(verification)
    second = repository.record(verification)

    assert second.id == first.id
    assert len(session.scalars(select(IntegrationExecutionReadinessVerificationRecord)).all()) == 1


def test_blocked_assessment_remains_blocked_after_persistence(session):
    verification = _verified(
        state="blocked",
        blockers=("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE",),
    )
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    repository.record(verification)

    loaded = repository.latest(candidate_sha=SHA, target_environment="staging")
    assert loaded is not None
    restored = loaded.to_verification()
    assert restored.assessment.state == "blocked"
    assert restored.assessment.ready is False


def test_candidate_filter_does_not_return_other_candidate(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    repository.record(_verified())

    assert (
        repository.latest(
            candidate_sha="c" * 40,
            target_environment="staging",
        )
        is None
    )


def test_tampered_persisted_verification_fails_closed(session):
    verification = _verified()
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    record = repository.record(verification)
    session.flush()
    record.verification_fingerprint = "f" * 64

    with pytest.raises(
        IntegrationExecutionReadinessPersistenceError,
        match="verification fingerprint mismatch",
    ):
        repository.latest(candidate_sha=SHA, target_environment="staging")

def test_malformed_blocker_payload_fails_closed(session):
    verification = _verified()
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    record = repository.record(verification)
    session.flush()
    record.blockers = None

    with pytest.raises(
        IntegrationExecutionReadinessPersistenceError,
        match="structurally invalid",
    ):
        repository.latest(candidate_sha=SHA, target_environment="staging")

