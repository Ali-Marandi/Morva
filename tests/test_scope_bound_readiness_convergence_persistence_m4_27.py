from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base
from morva.persistence.scope_bound_readiness_convergence_records_m4_27 import (
    ScopeBoundReadinessConvergencePersistenceError,
    ScopeBoundReadinessConvergenceRecord,
    ScopeBoundReadinessConvergenceRepository,
)
from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergence,
)


NOW = datetime(2026, 9, 23, 17, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[ScopeBoundReadinessConvergenceRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _convergence(
    *,
    candidate_sha: str = "d" * 40,
    scope_id: str = "district-1",
    checked_at: datetime = NOW,
    state: str = "converged",
    blocker: str | None = None,
    evidence_fp: str = "a" * 64,
) -> ScopeBoundReadinessConvergence:
    blockers = (blocker,) if blocker else ()
    return ScopeBoundReadinessConvergence(
        convergence_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=candidate_sha,
        target_environment="staging",
        organization_scope="district",
        organization_scope_id=scope_id,
        checked_at=checked_at,
        persisted_verification_fingerprint="b" * 64,
        persisted_evidence_readiness_fingerprint=evidence_fp,
        current_evidence_readiness_fingerprint=evidence_fp,
        state=state,
        blockers=blockers,
        fingerprint=_fingerprint(
            candidate_sha=candidate_sha,
            scope_id=scope_id,
            checked_at=checked_at,
            persisted_verification_fingerprint="b" * 64,
            persisted_evidence_readiness_fingerprint=evidence_fp,
            current_evidence_readiness_fingerprint=evidence_fp,
            state=state,
            blockers=blockers,
        ),
    )


def _fingerprint(
    *,
    candidate_sha: str,
    scope_id: str,
    checked_at: datetime,
    persisted_verification_fingerprint: str,
    persisted_evidence_readiness_fingerprint: str,
    current_evidence_readiness_fingerprint: str,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    import hashlib
    import json

    payload = {
        "convergence_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": candidate_sha.lower(),
        "target_environment": "staging",
        "organization_scope": "district",
        "organization_scope_id": scope_id,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "persisted_verification_fingerprint": persisted_verification_fingerprint,
        "persisted_evidence_readiness_fingerprint": persisted_evidence_readiness_fingerprint,
        "current_evidence_readiness_fingerprint": current_evidence_readiness_fingerprint,
        "state": state,
        "blockers": list(blockers),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def test_record_round_trip_is_fail_closed(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    original = _convergence()

    record = repository.record(original, recorded_by="auditor-1")
    restored = record.to_convergence()

    assert restored.fingerprint == original.fingerprint
    assert record.recorded_by == "auditor-1"


def test_record_is_idempotent_for_same_fingerprint_and_actor(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    original = _convergence()

    first = repository.record(original, recorded_by="auditor-1")
    second = repository.record(original, recorded_by="auditor-1")

    assert first.id == second.id


def test_same_fingerprint_cannot_change_recording_actor(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    original = _convergence()
    repository.record(original, recorded_by="auditor-1")

    with pytest.raises(
        ScopeBoundReadinessConvergencePersistenceError,
        match="different actor",
    ):
        repository.record(original, recorded_by="auditor-2")


def test_tampered_persisted_convergence_fails_closed(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    record = repository.record(_convergence(), recorded_by="auditor-1")
    record.state = "blocked"
    record.blockers = ["tampered"]

    with pytest.raises(
        ScopeBoundReadinessConvergencePersistenceError,
        match="structurally invalid",
    ):
        record.to_convergence()


def test_history_isolated_by_exact_scope(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    repository.record(
        _convergence(scope_id="district-1"),
        recorded_by="auditor-1",
    )
    repository.record(
        _convergence(
            scope_id="district-2",
            candidate_sha="e" * 40,
            checked_at=NOW.replace(minute=30),
        ),
        recorded_by="auditor-1",
    )

    records = repository.list_verified(
        organization_scope="district",
        organization_scope_id="district-1",
    )

    assert len(records) == 1
    assert records[0].organization_scope_id == "district-1"


def test_history_cursor_is_deterministic(session):
    repository = ScopeBoundReadinessConvergenceRepository(session)
    first = repository.record(
        _convergence(checked_at=NOW),
        recorded_by="auditor-1",
    )
    repository.record(
        _convergence(
            checked_at=NOW.replace(minute=30),
            candidate_sha="e" * 40,
        ),
        recorded_by="auditor-1",
    )

    page = repository.list_verified(
        organization_scope="district",
        organization_scope_id="district-1",
        limit=1,
    )
    assert page[0].id != first.id

    next_page = repository.list_verified(
        organization_scope="district",
        organization_scope_id="district-1",
        checked_before=page[0].checked_at,
        before_id=page[0].id,
        limit=1,
    )

    assert len(next_page) == 1
    assert next_page[0].id == first.id
