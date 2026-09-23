from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
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


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    from morva.persistence.integration_execution_readiness_records import (
        IntegrationExecutionReadinessVerificationRecord,
    )

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
    checked_at: datetime,
    verified_at: datetime,
    candidate_sha: str = SHA,
    target_environment: str = "staging",
) -> IndependentIntegrationExecutionReadinessVerification:
    fingerprint_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": candidate_sha,
        "target_environment": target_environment,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "evidence_readiness_fingerprint": "3" * 64,
        "binding_fingerprint": "1" * 64,
        "binding_verification_fingerprint": "2" * 64,
        "state": "ready",
        "blockers": [],
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
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=candidate_sha,
        target_environment=target_environment,
        checked_at=checked_at,
        evidence_readiness_fingerprint="3" * 64,
        binding_fingerprint="1" * 64,
        binding_verification_fingerprint="2" * 64,
        state="ready",
        blockers=(),
    )
    return IndependentIntegrationExecutionReadinessVerification(
        assessment=assessment,
        verified_at=verified_at,
    )


def test_history_is_deterministic_with_tie_breaker(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    first = repository.record(
        _verified(
            checked_at=NOW - timedelta(minutes=3),
            verified_at=NOW,
        ),
        organization_scope="ministry",
        organization_scope_id="ministry",
    )
    second = repository.record(
        _verified(
            checked_at=NOW - timedelta(minutes=2),
            verified_at=NOW,
        )
    )
    third = repository.record(
        _verified(
            checked_at=NOW - timedelta(minutes=1),
            verified_at=NOW,
        )
    )
    session.flush()

    first.id = UUID("00000000-0000-0000-0000-000000000001")
    second.id = UUID("00000000-0000-0000-0000-000000000002")
    third.id = UUID("00000000-0000-0000-0000-000000000003")

    page = repository.list_verified(
        organization_scope="ministry",
        organization_scope_id="ministry",
        limit=2,
    )
    assert [record.id for record in page] == [third.id, second.id]

    next_page = repository.list_verified(
        organization_scope="ministry",
        organization_scope_id="ministry",
        verified_before=page[-1].verified_at,
        before_id=page[-1].id,
        limit=2,
    )
    assert [record.id for record in next_page] == [first.id]


def test_history_filters_candidate_and_environment(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    repository.record(
        _verified(
            checked_at=NOW - timedelta(minutes=2),
            verified_at=NOW - timedelta(minutes=1),
        )
    )
    repository.record(
        _verified(
            checked_at=NOW - timedelta(minutes=1),
            verified_at=NOW,
            candidate_sha="c" * 40,
            target_environment="pilot",
        )
    )

    records = repository.list_verified(
        candidate_sha="c" * 40,
        target_environment="pilot",
        organization_scope="pilot",
        organization_scope_id="pilot-1",
    )
    assert len(records) == 1
    assert records[0].candidate_sha == "c" * 40
    assert records[0].target_environment == "pilot"


def test_history_fails_closed_when_any_selected_receipt_is_tampered(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    record = repository.record(
        _verified(
            checked_at=NOW,
            verified_at=NOW,
        )
    )
    session.flush()
    record.blockers = None

    with pytest.raises(
        IntegrationExecutionReadinessPersistenceError,
        match="structurally invalid",
    ):
        repository.list_verified(
        organization_scope="ministry",
        organization_scope_id="ministry",
        limit=10,
    )
