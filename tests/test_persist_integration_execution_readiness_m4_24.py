from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessVerificationRecord,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.persistence.models import Base
from morva.runtime.persist_integration_execution_readiness_m4_24 import (
    persist_verified_integration_execution_readiness,
)


NOW = datetime(2026, 9, 23, 13, tzinfo=timezone.utc)
SHA = "a" * 40


def _assessment_payload(
    *,
    candidate_sha: str = SHA,
    state: str = "ready",
    blockers: list[str] | None = None,
    tamper_assessment_fingerprint: bool = False,
) -> dict[str, object]:
    blockers = blockers or []
    checked_at = (NOW.replace(minute=0)).isoformat()
    payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": candidate_sha,
        "target_environment": "staging",
        "checked_at": checked_at,
        "evidence_readiness_fingerprint": "3" * 64,
        "binding_fingerprint": "1" * 64,
        "binding_verification_fingerprint": "2" * 64,
        "state": state,
        "blockers": blockers,
        "ready": state == "ready",
    }
    fingerprint_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": candidate_sha,
        "target_environment": "staging",
        "checked_at": checked_at,
        "evidence_readiness_fingerprint": "3" * 64,
        "binding_fingerprint": "1" * 64,
        "binding_verification_fingerprint": "2" * 64,
        "state": state,
        "blockers": blockers,
    }
    fingerprint = sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    payload["fingerprint"] = "f" * 64 if tamper_assessment_fingerprint else fingerprint
    return payload


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


def test_persists_only_after_independent_verification(
    session,
    tmp_path: Path,
):
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(
        json.dumps(_assessment_payload()),
        encoding="utf-8",
    )
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    record, verification = persist_verified_integration_execution_readiness(
        repository,
        assessment_path,
        repository_name="Ali-Marandi/Morva",
        candidate_sha=SHA,
        verified_at=NOW,
    )

    assert record.verification_fingerprint == verification.fingerprint
    assert record.organization_scope == "ministry"
    assert record.organization_scope_id == "ministry"
    assert record.scope_binding_fingerprint
    assert len(session.scalars(select(IntegrationExecutionReadinessVerificationRecord)).all()) == 1


def test_candidate_sha_mismatch_blocks_persistence(session, tmp_path: Path):
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(json.dumps(_assessment_payload()), encoding="utf-8")
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    with pytest.raises(ValueError, match="candidate SHA mismatch"):
        persist_verified_integration_execution_readiness(
            repository,
            assessment_path,
            repository_name="Ali-Marandi/Morva",
            candidate_sha="b" * 40,
            verified_at=NOW,
            organization_scope="ministry",
            organization_scope_id="ministry",
        )

    assert session.scalars(select(IntegrationExecutionReadinessVerificationRecord)).all() == []


def test_tampered_assessment_fingerprint_blocks_persistence(
    session,
    tmp_path: Path,
):
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(
        json.dumps(_assessment_payload(tamper_assessment_fingerprint=True)),
        encoding="utf-8",
    )
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    with pytest.raises(ValueError, match="assessment structure is invalid"):
        persist_verified_integration_execution_readiness(
            repository,
            assessment_path,
            repository_name="Ali-Marandi/Morva",
            candidate_sha=SHA,
            verified_at=NOW,
            organization_scope="ministry",
            organization_scope_id="ministry",
        )

    assert session.scalars(select(IntegrationExecutionReadinessVerificationRecord)).all() == []


def test_blocked_assessment_is_persisted_as_blocked_receipt(
    session,
    tmp_path: Path,
):
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(
        json.dumps(
            _assessment_payload(
                state="blocked",
                blockers=["AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE"],
            )
        ),
        encoding="utf-8",
    )
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    record, verification = persist_verified_integration_execution_readiness(
        repository,
        assessment_path,
        repository_name="Ali-Marandi/Morva",
        candidate_sha=SHA,
        verified_at=NOW,
    )

    assert verification.assessment.ready is False
    assert record.state == "blocked"
    assert record.blockers == ["AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE"]


def test_duplicate_verified_receipt_is_idempotent(
    session,
    tmp_path: Path,
):
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(json.dumps(_assessment_payload()), encoding="utf-8")
    repository = IntegrationExecutionReadinessVerificationRepository(session)

    first, _ = persist_verified_integration_execution_readiness(
        repository,
        assessment_path,
        repository_name="Ali-Marandi/Morva",
        candidate_sha=SHA,
        verified_at=NOW,
    )
    second, _ = persist_verified_integration_execution_readiness(
        repository,
        assessment_path,
        repository_name="Ali-Marandi/Morva",
        candidate_sha=SHA,
        verified_at=NOW,
    )

    assert second.id == first.id
    assert len(session.scalars(select(IntegrationExecutionReadinessVerificationRecord)).all()) == 1
