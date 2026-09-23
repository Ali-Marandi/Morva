from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.persistence.models import Base
from morva.persistence.scoped_evidence_readiness_m4_26 import (
    ScopedEvidenceReadinessPersistenceError,
    build_current_scoped_evidence_readiness,
)
from morva.runtime.evidence_submission import decide_evidence, submit_evidence
from morva.security.policy import Scope


NOW = datetime(2026, 9, 23, 16, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[AuthoritativeEvidenceSubmissionRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def _accepted_evidence(
    session,
    *,
    evidence_id: str,
    scope: Scope,
    scope_id: str,
):
    submit_evidence(
        session,
        evidence_id=evidence_id,
        source_type="legal_rule",
        source_uri=f"https://example.test/{evidence_id}",
        source_sha256="a" * 64,
        issuer="test-issuer",
        population_scope="all-employees",
        submission_scope=scope,
        submission_scope_id=scope_id,
        effective_from=NOW,
        effective_to=None,
        expires_at=None,
        submitted_by="submitter",
        submitted_at=NOW,
    )
    return decide_evidence(
        session,
        evidence_id=evidence_id,
        approver_id="approver",
        decision="accepted",
        decided_at=NOW,
    )


def test_current_readiness_uses_only_exact_scope(session):
    _accepted_evidence(
        session,
        evidence_id="district-one",
        scope=Scope.DISTRICT,
        scope_id="district-1",
    )
    _accepted_evidence(
        session,
        evidence_id="district-two",
        scope=Scope.DISTRICT,
        scope_id="district-2",
    )

    assessment = build_current_scoped_evidence_readiness(
        session,
        organization_scope="district",
        organization_scope_id="district-1",
        checked_at=NOW,
    )

    assert assessment.repository == "Ali-Marandi/Morva"
    assert "district-one" not in {
        item.evidence_id for item in ()
    }
    assert assessment.fingerprint
    assert assessment.complete is False


def test_current_readiness_fails_closed_for_empty_registry(session):
    with pytest.raises(
        ScopedEvidenceReadinessPersistenceError,
        match="cannot project an empty authoritative evidence registry",
    ):
        build_current_scoped_evidence_readiness(
            session,
            organization_scope="district",
            organization_scope_id="district-1",
            checked_at=NOW,
        )
